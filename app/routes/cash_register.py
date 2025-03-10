from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, FileResponse, Response
from typing import List, Optional
from datetime import datetime, date, timedelta
from bson import ObjectId
from fastapi.templating import Jinja2Templates
from ..models.cash_register import CashRegister, CashEntry, Transaction
from ..database import get_db
from ..utils.template_utils import process_template_data
import logging
import pandas as pd
import io
import xlsxwriter

logger = logging.getLogger(__name__)

web_router = APIRouter()
api_router = APIRouter(prefix="/api/cash-register", tags=["cash_register"])
templates = Jinja2Templates(directory="app/templates")

@web_router.get("/cash-register", name="cash_register.index")
async def cash_register_page(request: Request):
    try:
        db = await get_db()
        
        # Get today's register entry
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        current_register = await db.cash_register.find_one({
            "date": {"$gte": today, "$lt": tomorrow}
        }, sort=[("initial_count_time", -1)])
        
        template_data = {
            "request": request,
            "current_register": None,
            "transactions": []
        }
        
        if current_register:
            # Calculate totals
            total_income = sum(t["amount"] for t in current_register.get("transactions", []) 
                             if t["type"] == "income")
            total_expenses = sum(t["amount"] for t in current_register.get("transactions", []) 
                               if t["type"] == "expense")
            
            # Convert ObjectId to string
            current_register["_id"] = str(current_register["_id"])
            
            # Add calculated totals
            current_register["total_income"] = total_income
            current_register["total_expenses"] = total_expenses
            current_register["current_balance"] = (
                current_register["initial_amount_counted"] + total_income - total_expenses
            )
            
            template_data["current_register"] = current_register
            template_data["transactions"] = current_register.get("transactions", [])

        # Process template data
        processed_data = process_template_data(template_data)
        
        return templates.TemplateResponse("cash_register.html", processed_data)
        
    except Exception as e:
        logger.error(f"Error loading cash register page: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@web_router.post("/entries")  # Changed from @web_route.r.post to @web_router.post
async def create_cash_entry(request: Request, entry: CashEntry):
    try:
        db = await get_db()
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        token_data = await db.active_tokens.find_one({"token": token})
        if not token_data:
            raise HTTPException(status_code=401, detail="Invalid token")

        entry_dict = entry.dict()
        entry_dict["created_by"] = token_data["username"]
        result = await db.cash_register.insert_one(entry_dict)
        return {"id": str(result.inserted_id)}
    except Exception as e:
        logger.error(f"Create entry error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Update API routes to use token auth
@api_router.get("/entries", response_model=List[CashRegister])
async def get_cash_entries(
    request: Request,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    try:
        db = await get_db()
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Rest of the function remains the same
        query = {}
        if start_date and end_date:
            query["date"] = {
                "$gte": datetime.combine(start_date, datetime.min.time()),
                "$lte": datetime.combine(end_date, datetime.max.time())
            }
        entries = await db.cash_register.find(query).sort("date", -1).to_list(1000)
        return entries
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/entries/{entry_id}", response_model=CashRegister)
async def update_cash_entry(
    request: Request,
    entry_id: str,
    entry_update: CashRegister
):
    try:
        db = await get_db()
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        token_data = await db.active_tokens.find_one({"token": token})
        if not token_data or not token_data.get("is_admin"):
            raise HTTPException(status_code=403, detail="Not authorized")

        update_result = await db.cash_register.update_one(
            {"_id": ObjectId(entry_id)},
            {"$set": entry_update.dict(exclude_unset=True)}
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        return await db.cash_register.find_one({"_id": ObjectId(entry_id)})
    except Exception as e:
        logger.error(f"Update entry error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))  # Fixed missing parenthesis here

@api_router.delete("/entries/{entry_id}")
async def delete_cash_entry(request: Request, entry_id: str):
    try:
        db = await get_db()
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        token_data = await db.active_tokens.find_one({"token": token})
        if not token_data or not token_data.get("is_admin"):
            raise HTTPException(status_code=403, detail="Not authorized")

        result = await db.cash_register.delete_one({"_id": ObjectId(entry_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        return {"message": "Entry deleted successfully"}
    except Exception as e:
        logger.error(f"Delete entry error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def add_log_entry(db, register_id: ObjectId, action: str, details: str, user: str):
    """Helper function to add log entries"""
    log_entry = {
        "timestamp": datetime.now(),
        "action": action,
        "details": details,
        "user": user
    }
    
    await db.cash_register.update_one(
        {"_id": register_id},
        {"$push": {"logs": log_entry}}
    )

@api_router.post("/", response_model=dict)
async def create_cash_entry(request: Request):
    try:
        user = request.state.user
        data = await request.json()
        db = await get_db()
        
        # Check if there's already an active register for today
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        # Only check for OPEN registers
        existing_register = await db.cash_register.find_one({
            "date": {"$gte": today, "$lt": tomorrow},
            "status": "open"  # Only block if there's an open register
        })
        
        if existing_register:
            raise HTTPException(
                status_code=400, 
                detail="Ya existe un registro activo para hoy"
            )
        
        # Create new day entry with register_number
        register_count = await db.cash_register.count_documents({
            "date": {"$gte": today, "$lt": tomorrow}
        })
        
        entry = {
            "date": datetime.fromisoformat(data["date"]),
            "initial_amount": 200.00,
            "initial_amount_verified": data["initial_amount_verified"],
            "initial_amount_counted": data["initial_amount_counted"],
            "initial_count_time": datetime.fromisoformat(data["initial_count_time"]),
            "verified_by": user["username"],
            "status": "open",
            "transactions": [],
            "final_count": None,
            "final_verification_time": None,
            "final_verified_by": None,
            "notes": data.get("notes", ""),
            "responsible": data["responsible"],
            "register_number": register_count + 1  # Add sequential number for the day
        }
        
        result = await db.cash_register.insert_one(entry)
        
        # Add initial log entry
        await add_log_entry(
            db,
            result.inserted_id,
            "APERTURA",
            f"Caja iniciada con ${entry['initial_amount_counted']:.2f}",
            user["username"]
        )
        
        return {"success": True, "id": str(result.inserted_id)}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error creating cash entry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/{entry_id}/transactions")
async def add_transaction(entry_id: str, request: Request):
    try:
        user = request.state.user
        data = await request.json()
        db = await get_db()
        
        register = await db.cash_register.find_one({"_id": ObjectId(entry_id)})
        if not register:
            raise HTTPException(status_code=404, detail="Register not found")
            
        if register["status"] == "closed":
            raise HTTPException(status_code=400, detail="Register is closed")
        
        transaction = {
            "type": data["type"],
            "amount": float(data["amount"]),
            "description": data["description"],
            "time": datetime.now(),
            "recorded_by": user["username"]
        }
        
        result = await db.cash_register.update_one(
            {"_id": ObjectId(entry_id)},
            {
                "$push": {"transactions": transaction},
                "$set": {"last_updated": datetime.now()}
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to add transaction")
            
        updated_register = await db.cash_register.find_one({"_id": ObjectId(entry_id)})
        
        # Process transactions for JSON response
        processed_data = process_template_data({
            "transactions": updated_register["transactions"]
        })
        
        # Add transaction log
        log_details = (f"{'Ingreso' if data['type'] == 'income' else 'Gasto'} "
                      f"de ${float(data['amount']):.2f} - {data['description']}")
        await add_log_entry(
            db,
            ObjectId(entry_id),
            "TRANSACCIÓN",
            log_details,
            user["username"]
        )
        
        return {
            "success": True,
            "transactions": processed_data["transactions"]
        }
        
    except Exception as e:
        logger.error(f"Error adding transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/{entry_id}/close")
async def close_day(entry_id: str, request: Request):
    try:
        user = request.state.user
        data = await request.json()
        
        db = await get_db()
        
        # Get current entry
        entry = await db.cash_register.find_one({"_id": ObjectId(entry_id)})
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
            
        if entry["status"] == "closed":
            raise HTTPException(status_code=400, detail="Day already closed")
            
        # Calculate expected amount and difference
        total_income = sum(t["amount"] for t in entry["transactions"] if t["type"] == "income")
        total_expenses = sum(t["amount"] for t in entry["transactions"] if t["type"] == "expense")
        expected_amount = entry["initial_amount_counted"] + total_income - total_expenses
        difference = float(data["final_count"]) - expected_amount  # Calculate difference here
        
        # Update with final count
        result = await db.cash_register.update_one(
            {"_id": ObjectId(entry_id)},
            {
                "$set": {
                    "status": "closed",
                    "final_count": float(data["final_count"]),
                    "final_verification_time": datetime.now(),
                    "final_verified_by": user["username"],
                    "expected_amount": expected_amount,
                    "difference": difference,  # Use calculated difference
                    "closing_notes": data.get("notes", "")
                }
            }
        )
        
        # Add closing log entry with proper difference value
        await add_log_entry(
            db,
            ObjectId(entry_id),
            "CIERRE",
            f"Caja cerrada con ${float(data['final_count']):.2f}. Diferencia: ${difference:.2f}",
            user["username"]
        )
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error closing day: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/today", response_model=dict)
async def get_today_status(request: Request):
    try:
        db = await get_db()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        current_register = await db.cash_register.find_one({
            "date": {"$gte": today, "$lt": tomorrow}
        })
        
        if not current_register:
            return {"status": "no_register"}
            
        transactions = await db.cash_transactions.find({
            "cash_register_id": current_register["_id"]
        }).sort("time", 1).to_list(length=None)
        
        return {
            "status": "active",
            "register": current_register,
            "transactions": transactions
        }
        
    except Exception as e:
        logger.error(f"Error getting today's status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/{entry_id}/export")
async def export_register(entry_id: str, format: str = Query("xlsx", regex="^(csv|xlsx)$")):
    output = None
    try:
        db = await get_db()
        
        entry = await db.cash_register.find_one({"_id": ObjectId(entry_id)})
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")

        transactions = entry.get("transactions", [])
        total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
        total_expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
        final_balance = entry['initial_amount_counted'] + total_income - total_expenses

        if format == "xlsx":
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output)

            # Add formats
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'align': 'center',
                'border': 1
            })
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1
            })
            money_format = workbook.add_format({
                'num_format': '$#,##0.00',
                'border': 1
            })
            cell_format = workbook.add_format({
                'border': 1
            })

            # Summary worksheet
            ws_summary = workbook.add_worksheet('Resumen')
            
            # Write title
            ws_summary.merge_range('A1:B1', 'RESUMEN DE CAJA', title_format)
            
            # Write summary data starting from row 2
            current_row = 2
            ws_summary.write(current_row, 0, 'Fecha', header_format)
            ws_summary.write(current_row, 1, entry['date'].strftime('%Y-%m-%d'), cell_format)
            
            current_row += 1
            ws_summary.write(current_row, 0, 'Hora Apertura', header_format)
            ws_summary.write(current_row, 1, entry['initial_count_time'].strftime('%H:%M:%S'), cell_format)
            
            current_row += 1
            ws_summary.write(current_row, 0, 'Responsable', header_format)
            ws_summary.write(current_row, 1, entry['responsible'], cell_format)
            
            current_row += 1
            ws_summary.write(current_row, 0, 'Monto Inicial', header_format)
            ws_summary.write(current_row, 1, entry['initial_amount_counted'], money_format)
            
            current_row += 1
            ws_summary.write(current_row, 0, 'Total Ingresos', header_format)
            ws_summary.write(current_row, 1, total_income, money_format)
            
            current_row += 1
            ws_summary.write(current_row, 0, 'Total Gastos', header_format)
            ws_summary.write(current_row, 1, total_expenses, money_format)
            
            current_row += 1
            ws_summary.write(current_row, 0, 'Balance Final', header_format)
            ws_summary.write(current_row, 1, final_balance, money_format)
            
            current_row += 1
            ws_summary.write(current_row, 0, 'Estado', header_format)
            ws_summary.write(current_row, 1, 'CERRADO' if entry.get('status') == 'closed' else 'ABIERTO', cell_format)
            
            current_row += 1
            ws_summary.write(current_row, 0, 'Notas', header_format)
            ws_summary.write(current_row, 1, entry.get('notes', ''), cell_format)

            # Set column widths
            ws_summary.set_column('A:A', 15)
            ws_summary.set_column('B:B', 25)

            # Rest of your existing code for transactions worksheet
            if transactions:
                ws_trans = workbook.add_worksheet('Transacciones')
                headers = ['Hora', 'Tipo', 'Descripción', 'Monto', 'Balance', 'Responsable']
                
                for col, header in enumerate(headers):
                    ws_trans.write(0, col, header, header_format)

                row = 1
                running_balance = entry['initial_amount_counted']
                for t in sorted(transactions, key=lambda x: x['time']):
                    time = t['time'].strftime('%H:%M:%S')
                    if t['type'] == 'income':
                        running_balance += t['amount']
                    else:
                        running_balance -= t['amount']

                    ws_trans.write(row, 0, time, cell_format)
                    ws_trans.write(row, 1, 'INGRESO' if t['type'] == 'income' else 'GASTO', cell_format)
                    ws_trans.write(row, 2, t['description'], cell_format)
                    ws_trans.write(row, 3, t['amount'], money_format)
                    ws_trans.write(row, 4, running_balance, money_format)
                    ws_trans.write(row, 5, t['recorded_by'], cell_format)
                    row += 1

                ws_trans.set_column('A:A', 10)
                ws_trans.set_column('B:B', 10)
                ws_trans.set_column('C:C', 40)
                ws_trans.set_column('D:E', 15)
                ws_trans.set_column('F:F', 15)

            # Add Logs worksheet
            if entry.get("logs"):
                ws_logs = workbook.add_worksheet('Registro')
                headers = ['Fecha/Hora', 'Acción', 'Detalles', 'Usuario']
                
                for col, header in enumerate(headers):
                    ws_logs.write(0, col, header, header_format)

                for row, log in enumerate(entry["logs"], 1):
                    ws_logs.write(row, 0, log["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), cell_format)
                    ws_logs.write(row, 1, log["action"], cell_format)
                    ws_logs.write(row, 2, log["details"], cell_format)
                    ws_logs.write(row, 3, log["user"], cell_format)

                # Set column widths for logs
                ws_logs.set_column('A:A', 20)  # Timestamp
                ws_logs.set_column('B:B', 15)  # Action
                ws_logs.set_column('C:C', 50)  # Details
                ws_logs.set_column('D:D', 15)  # User

            workbook.close()
            output.seek(0)

            filename = f"reporte_caja_{entry['date'].strftime('%Y%m%d')}.xlsx"
            
            return Response(
                content=output.getvalue(),
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
            )

        else:  # CSV format
            # Keep your existing CSV code here
            # Create StringIO buffer for CSV
            output = io.StringIO()
            
            # Write summary information
            output.write("RESUMEN DE CAJA\n")
            output.write(f"Fecha,{entry['date'].strftime('%Y-%m-%d')}\n")
            output.write(f"Hora de Apertura,{entry['initial_count_time'].strftime('%H:%M:%S')}\n")
            output.write(f"Responsable,{entry['responsible']}\n")
            output.write(f"Monto Inicial,${entry['initial_amount_counted']:.2f}\n")
            output.write(f"Total Ingresos,${total_income:.2f}\n")
            output.write(f"Total Gastos,${total_expenses:.2f}\n")
            output.write(f"Balance Final,${final_balance:.2f}\n")
            output.write(f"Estado,{'CERRADO' if entry.get('status') == 'closed' else 'ABIERTO'}\n")
            output.write(f"Notas,{entry.get('notes', '')}\n\n")
            
            # Write transactions
            if transactions:
                output.write("TRANSACCIONES\n")
                output.write("Hora,Tipo,Descripción,Monto,Balance,Responsable\n")
                
                running_balance = entry['initial_amount_counted']
                for t in sorted(transactions, key=lambda x: x['time']):
                    time = t['time'].strftime('%H:%M:%S')
                    tipo = 'INGRESO' if t['type'] == 'income' else 'GASTO'
                    
                    if t['type'] == 'income':
                        running_balance += t['amount']
                    else:
                        running_balance -= t['amount']
                    
                    # Escape description to handle commas
                    desc = f'"{t["description"]}"' if ',' in t["description"] else t["description"]
                    
                    output.write(f'{time},{tipo},{desc},${t["amount"]:.2f},${running_balance:.2f},{t["recorded_by"]}\n')
            
            # Add logs section
            if entry.get("logs"):
                output.write("\nREGISTRO DE ACTIVIDADES\n")
                output.write("Fecha/Hora,Acción,Detalles,Usuario\n")
                
                for log in entry["logs"]:
                    time = log["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                    details = f'"{log["details"]}"' if ',' in log["details"] else log["details"]
                    output.write(f'{time},{log["action"]},{details},{log["user"]}\n')
            
            # Generate response
            content = output.getvalue().encode('utf-8-sig')
            output.close()
            
            filename = f"reporte_caja_{entry['date'].strftime('%Y%m%d')}.csv"
            
            return Response(
                content=content,
                media_type='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': 'text/csv; charset=utf-8'
                }
            )
            
    except Exception as e:
        logger.error(f"Error exporting register: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if output:
            output.close()

# Include the web router in the API router
web_router.include_router(api_router)
router = web_router