from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from bson import ObjectId
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Categories mapping based on supplier
SUPPLIER_CATEGORY_MAP = {
    'ACACIAS': 'PERECEDEROS',
    'AMAZON': 'INSUMOS BÁSICOS',
    'CARLOS ROLLOS PACK': 'PACKAGING',
    'COSTCO': 'INSUMOS BÁSICOS',
    'DEPOT': 'EQUIPO',
    'INSTACAR': 'INSUMOS BÁSICOS',
    'LIZ': 'LIMPIEZA',
    'MARIANO': 'PERECEDEROS',
    'ROMANO': 'BEBIDAS',
    'SANBER': 'BEBIDAS',
    'SYSCO': 'INSUMOS BÁSICOS',
    'TQMUCH': 'CONDIMENTOS',
    'WALLMART': 'INSUMOS BÁSICOS',
    'WEBRESTAURANT': 'EQUIPO'
}

# Item specific category overrides
ITEM_CATEGORY_MAP = {
    'MILANESAS': 'PERECEDEROS',
    'BACON FETAS': 'PERECEDEROS',
    'BACON TROZOS': 'PERECEDEROS',
    'PAN PARA BURGER': 'PERECEDEROS',
    'PAN PARA CHORIZOS': 'PERECEDEROS',
    'QUESO EN FETAS PARA BURGER': 'PERECEDEROS',
    'BOLSAS BLANCAS CWCO': 'PACKAGING',
    'BOLSAS UBER 13 X7': 'PACKAGING',
    'DELIPAPER CHURROWORLD': 'PACKAGING',
    'POMOS PLASTICOS 24 OZ': 'PACKAGING',
    'POMOS PLASTICOS 32 OZ': 'PACKAGING',
    'ROLLITOS PARA IMPRESION': 'PACKAGING',
    'SEPARADOR PLASTICO': 'PACKAGING',
    'TRAY BANDEJAS INDIVIDUAL': 'PACKAGING',
    'VASOS DE CAFÉ': 'PACKAGING',
    'VASOS DE HELADO': 'PACKAGING',
    'VASOS DE MILKSHAKE': 'PACKAGING',
    'CARGA DE GAS SEMANAL': 'MANTENIMIENTO',
    'ULTIMO CAMBIO DE ACEITE FECHA': 'MANTENIMIENTO',
    'DESENGRASANTE AMARILLO GRANDE': 'LIMPIEZA',
    'DESENGRASANTE NEGRO SPRAY': 'LIMPIEZA',
    'SPRAY ORANGE GLO': 'LIMPIEZA',
    'CHUPETIN RAINBOW': 'INSUMOS BÁSICOS',
    'MARSHMALLOW JUMBO': 'INSUMOS BÁSICOS',
    'MARSHMALLOW MINI': 'INSUMOS BÁSICOS',
    'MASHAMALLOW BIT COLORIDOS': 'INSUMOS BÁSICOS',
    'SPRINKLES': 'INSUMOS BÁSICOS',
    'FRUIT PEBLES (CEREALES)': 'INSUMOS BÁSICOS',
    'OREO': 'INSUMOS BÁSICOS'
}

async def update_categories():
    try:
        MONGODB_URL = os.getenv('MONGODB_URL')
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client.crm_leandro
        
        # Update items based on name first, then fallback to supplier
        async for item in db.inventory.find({}):
            name = item.get('name', '')
            supplier = item.get('supplier', '')
            
            # First check if we have a specific category for this item
            category = ITEM_CATEGORY_MAP.get(name)
            
            # If no specific category, use supplier mapping
            if not category:
                category = SUPPLIER_CATEGORY_MAP.get(supplier, 'Sin Categoría')
            
            await db.inventory.update_one(
                {'_id': item['_id']},
                {'$set': {'category': category}}
            )
            print(f"Updated {name} with category {category}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(update_categories())