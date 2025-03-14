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

def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    
    if isinstance(doc, dict):
        return {
            key: serialize_doc(value) 
            for key, value in doc.items()
        }
    elif isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, datetime):
        return doc.isoformat()
    return doc

@web_router.get("/cash-register", name="cash_register.index")
async def cash_register_page(request: Request):
    try:
        db = await get_db()
        
        # Get only open register, regardless of date
        current_register = await db.cash_register.find_one(
            {"status": "open"},
            sort=[("initial_count_time", -1)]
        )
        
        # Get transactions if register exists and is open
        transactions = []
        if current_register:
            transactions = current_register.get("transactions", [])
            # Serialize the register and transactions
            current_register = serialize_doc(current_register)
            transactions = serialize_doc(transactions)
        
        # Get vault total
        vault_total = await get_vault_total(db)
        
        return templates.TemplateResponse(
            "cash_register.html",
            {
                "request": request,
                "current_register": current_register,
                "transactions": transactions,
                "vault_total": vault_total,
                "is_admin": request.state.user.get("is_admin", False)
            }
        )
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
        
        # Check only for OPEN registers
        existing_open_register = await db.cash_register.find_one({
            "status": "open"  # Only check status, regardless of date
        })
        
        if existing_open_register:
            raise HTTPException(
                status_code=400, 
                detail="Existe un registro abierto. Debe cerrarlo antes de abrir uno nuevo."
            )
        
        # Get today's registers for numbering
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        register_count = await db.cash_register.count_documents({
            "date": {"$gte": today, "$lt": tomorrow}
        })
        
        # Create new entry
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
            "register_number": register_count + 1  # Sequential number for the day
        }
        
        result = await db.cash_register.insert_one(entry)
        
        # Add initial log entry
        await add_log_entry(
            db,
            result.inserted_id,
            "APERTURA",
            f"Caja #{register_count + 1} iniciada con ${entry['initial_amount_counted']:.2f}",
            user["username"]
        )
        
        return {"success": True, "id": str(result.inserted_id)}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error creating cash entry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))  # Fixed parenthesis

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
            
        # Get updated register data
        updated_register = await db.cash_register.find_one({"_id": ObjectId(entry_id)})
        
        # Calculate new totals for this register
        total_income = sum(t["amount"] for t in updated_register["transactions"] if t["type"] == "income")
        total_expenses = sum(t["amount"] for t in updated_register["transactions"] if t["type"] == "expense")
        new_total = total_income - total_expenses
        
        logger.debug(f"Transaction added - Type: {data['type']}, Amount: {data['amount']}, Register Total: {new_total}")
        
        # Get updated vault total
        vault_pipeline = [
            {"$match": {"status": "closed"}},
            {"$group": {
                "_id": None,
                "total_income": {"$sum": "$billing"},
                "total_expenses": {"$sum": "$expenses"}
            }}
        ]
        
        vault_result = await db.cash_register.aggregate(vault_pipeline).to_list(None)
        vault_total = vault_result[0]["total_income"] - vault_result[0]["total_expenses"] if vault_result else 0
        
        return {
            "success": True,
            "transactions": updated_register["transactions"],
            "register_total": new_total,
            "vault_total": vault_total
        }
        
    except Exception as e:
        logger.error(f"Error adding transaction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))  # Fixed syntax here

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

# Modify these routes only, keep everything else the same

@api_router.get("/vault/total")
async def get_vault_total():
    try:
        db = await get_db()
        # Get all transactions from closed registers
        pipeline = [
            {"$match": {"status": "closed"}},
            {"$group": {
                "_id": None,
                "total_income": {
                    "$sum": {
                        "$sum": {
                            "$map": {
                                "input": "$transactions",
                                "as": "t",
                                "in": {
                                    "$cond": [
                                        {"$eq": ["$$t.type", "income"]},
                                        "$$t.amount",
                                        0
                                    ]
                                }
                            }
                        }
                    }
                },
                "total_expenses": {
                    "$sum": {
                        "$sum": {
                            "$map": {
                                "input": "$transactions",
                                "as": "t",
                                "in": {
                                    "$cond": [
                                        {"$eq": ["$$t.type", "expense"]},
                                        "$$t.amount",
                                        0
                                    ]
                                }
                            }
                        }
                    }
                }
            }}
        ]
        
        result = await db.cash_register.aggregate(pipeline).to_list(None)
        if result:
            total = result[0]["total_income"] - result[0]["total_expenses"]
            logger.debug(f"Vault total calculated - Income: {result[0]['total_income']}, Expenses: {result[0]['total_expenses']}, Total: {total}")
        else:
            total = 0
            logger.debug("No closed registers found, vault total is 0")
            
        return {"total": total}
    except Exception as e:
        logger.error(f"Error getting vault total: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/vault/update")
async def update_vault_total(amount: float):
    try:
        db = await get_db()
        # Get current vault total
        vault = await db.vault.find_one({})
        current_total = vault["total_amount"] if vault else 0
        
        # Update vault with new total and add transaction record
        await db.vault.update_one(
            {},
            {
                "$set": {
                    "total_amount": amount,
                    "last_updated": datetime.now()
                },
                "$push": {
                    "transactions": {
                        "previous_total": current_total,
                        "new_total": amount,
                        "change": amount - current_total,
                        "timestamp": datetime.now()
                    }
                }
            },
            upsert=True
        )
        
        return {"success": True, "total": amount}
    except Exception as e:
        logger.error(f"Error updating vault total: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/vault/total")
async def get_vault_total_endpoint(request: Request):
    try:
        db = await get_db()
        total = await get_vault_total(db)
        return total
    except Exception as e:
        logger.error(f"Error getting vault total: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
# Include the web router in the API router
web_router.include_router(api_router)

async def get_vault_total(db):
    try:
        # Get totals from closed registers
        pipeline = [
            {
                "$facet": {
                    "closed_registers": [
                        {"$match": {"status": "closed"}},
                        {"$group": {
                            "_id": None,
                            "total_income": {
                                "$sum": {
                                    "$sum": {
                                        "$map": {
                                            "input": "$transactions",
                                            "as": "t",
                                            "in": {
                                                "$cond": [
                                                    {"$eq": ["$$t.type", "income"]},
                                                    "$$t.amount",
                                                    0
                                                ]
                                            }
                                        }
                                    }
                                }
                            },
                            "total_expenses": {
                                "$sum": {
                                    "$sum": {
                                        "$map": {
                                            "input": "$transactions",
                                            "as": "t",
                                            "in": {
                                                "$cond": [
                                                    {"$eq": ["$$t.type", "expense"]},
                                                    "$$t.amount",
                                                    0
                                                ]
                                            }
                                        }
                                    }
                                }
                            }
                        }}
                    ],
                    "open_register": [
                        {"$match": {"status": "open"}},
                        {"$unwind": "$transactions"},
                        {"$group": {
                            "_id": None,
                            "open_income": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$transactions.type", "income"]},
                                        "$transactions.amount",
                                        0
                                    ]
                                }
                            },
                            "open_expenses": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$transactions.type", "expense"]},
                                        "$transactions.amount",
                                        0
                                    ]
                                }
                            }
                        }}
                    ]
                }
            }
        ]
        
        result = await db.cash_register.aggregate(pipeline).to_list(None)
        
        # Initialize totals
        closed_income = 0
        closed_expenses = 0
        open_income = 0
        open_expenses = 0
        
        if result:
            # Get closed registers totals
            if result[0]["closed_registers"]:
                closed = result[0]["closed_registers"][0]
                closed_income = closed.get("total_income", 0)
                closed_expenses = closed.get("total_expenses", 0)
            
            # Get open register totals
            if result[0]["open_register"]:
                open_reg = result[0]["open_register"][0]
                open_income = open_reg.get("open_income", 0)
                open_expenses = open_reg.get("open_expenses", 0)
        
        # Calculate total including both closed and open registers
        total = (closed_income + open_income) - (closed_expenses + open_expenses)
        
        logger.debug(f"Vault total calculated - Closed Income: {closed_income}, "
                    f"Closed Expenses: {closed_expenses}, "
                    f"Open Income: {open_income}, "
                    f"Open Expenses: {open_expenses}, "
                    f"Total: {total}")
        
        return total
        
    except Exception as e:
        logger.error(f"Error getting vault total: {e}")
        raise HTTPException(status_code=500, detail=str(e))