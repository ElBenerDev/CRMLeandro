from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from fastapi import HTTPException
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
load_dotenv()

# Default inventory items
DEFAULT_INVENTORY = [
    # ACACIAS Supplier
    {
        "name": "MILANESAS",
        "current_stock": 0,
        "unit": "unidades",
        "to_order": 0,
        "supplier": "ACACIAS"
    },
    # AMAZON Supplier
    {
        "name": "FRUIT PEBLES (CEREALES)",
        "current_stock": 0,
        "unit": "paquetes",
        "to_order": 0,
        "supplier": "AMAZON"
    },
    {
        "name": "OREO",
        "current_stock": 0,
        "unit": "cajas",
        "to_order": 0,
        "supplier": "AMAZON"
    },
    {
        "name": "MARSHMALLOW JUMBO",
        "current_stock": 0,
        "unit": "paquetes",
        "to_order": 0,
        "supplier": "AMAZON"
    },
    {
        "name": "MARSHMALLOW MINI",
        "current_stock": 0,
        "unit": "paquetes",
        "to_order": 0,
        "supplier": "AMAZON"
    },
    {
        "name": "MASHAMALLOW BIT COLORIDOS",
        "current_stock": 0,
        "unit": "potes",
        "to_order": 0,
        "supplier": "AMAZON"
    },
    {
        "name": "CHUPETIN RAINBOW",
        "current_stock": 0,
        "unit": "cajas",
        "to_order": 0,
        "supplier": "AMAZON"
    },
    {
        "name": "SPRINKLES",
        "current_stock": 0,
        "unit": "potes",
        "to_order": 0,
        "supplier": "AMAZON"
    },
    # COSTCO Supplier
    {
        "name": "AGUA GRANDE PARA PRODUCIR",
        "current_stock": 0,
        "unit": "pack x 6",
        "to_order": 0,
        "supplier": "COSTCO"
    },
    {
        "name": "PERRIER AGUA CON GAS",
        "current_stock": 0,
        "unit": "pack x 24",
        "to_order": 0,
        "supplier": "COSTCO"
    },
    {
        "name": "SPRITE LATAS",
        "current_stock": 0,
        "unit": "pack x 24",
        "to_order": 0,
        "supplier": "COSTCO"
    },
    {
        "name": "COCA COMUN LATAS",
        "current_stock": 0,
        "unit": "pack x 24",
        "to_order": 0,
        "supplier": "COSTCO"
    },
    {
        "name": "COCA ZERO LATAS",
        "current_stock": 0,
        "unit": "pack x 24",
        "to_order": 0,
        "supplier": "COSTCO"
    },
    # SYSCO Supplier
    {
        "name": "MANTECA SIN SAL",
        "current_stock": 0,
        "unit": "cajas",
        "to_order": 0,
        "supplier": "SYSCO"
    },
    {
        "name": "WHIPPED CREAM",
        "current_stock": 0,
        "unit": "unidades",
        "to_order": 0,
        "supplier": "SYSCO"
    },
    {
        "name": "NUTELLA",
        "current_stock": 0,
        "unit": "potes",
        "to_order": 0,
        "supplier": "SYSCO"
    },
    {
        "name": "BROWNIE",
        "current_stock": 0,
        "unit": "cajas",
        "to_order": 0,
        "supplier": "SYSCO"
    },
    {
        "name": "LECHE CONDENSADA",
        "current_stock": 0,
        "unit": "latas",
        "to_order": 0,
        "supplier": "SYSCO"
    },
    {
        "name": "CREAM CHEESE",
        "current_stock": 0,
        "unit": "paquetes",
        "to_order": 0,
        "supplier": "SYSCO"
    },
    {
        "name": "FERRERO",
        "current_stock": 0,
        "unit": "cajas",
        "to_order": 0,
        "supplier": "SYSCO"
    },
    {
        "name": "ALMENDRAS EN HEBRAS",
        "current_stock": 0,
        "unit": "paquetes",
        "to_order": 0,
        "supplier": "SYSCO"
    },
    {
        "name": "AZUCAR BOLSA 25 LB",
        "current_stock": 0,
        "unit": "bolsas",
        "to_order": 0,
        "supplier": "SYSCO"
    },
    {
        "name": "PIMIENTA",
        "current_stock": 0,
        "unit": "paquetes",
        "to_order": 0,
        "supplier": "SYSCO"
    },
    # SANBER Supplier
    {
        "name": "CHOCOLATE SAUCE",
        "current_stock": 0,
        "unit": "tanqueta 55lbs",
        "to_order": 0,
        "supplier": "SANBER"
    },
    # Cleaning Supplies
    {
        "name": "DESENGRASANTE AMARILLO GRANDE",
        "current_stock": 0,
        "unit": "unidades",
        "to_order": 0,
        "supplier": "CLEANING_SUPPLIES"
    },
    {
        "name": "DESENGRASANTE NEGRO SPRAY",
        "current_stock": 0,
        "unit": "unidades",
        "to_order": 0,
        "supplier": "CLEANING_SUPPLIES"
    },
    {
        "name": "SPRAY ORANGE GLO",
        "current_stock": 0,
        "unit": "unidades",
        "to_order": 0,
        "supplier": "CLEANING_SUPPLIES"
    },
    # Ice Cream Supplies
    {
        "name": "VAINILLA ICE CREAM",
        "current_stock": 0,
        "unit": "galones",
        "to_order": 0,
        "supplier": "ICE_CREAM"
    },
    {
        "name": "CHOCOLATE ICE CREAM",
        "current_stock": 0,
        "unit": "galones",
        "to_order": 0,
        "supplier": "ICE_CREAM"
    },
    {
        "name": "COOKIES AND CREAM",
        "current_stock": 0,
        "unit": "galones",
        "to_order": 0,
        "supplier": "ICE_CREAM"
    },
    {
        "name": "DOUGHT",
        "current_stock": 0,
        "unit": "galones",
        "to_order": 0,
        "supplier": "ICE_CREAM"
    },
    {
        "name": "STRAWBERRY",
        "current_stock": 0,
        "unit": "galones",
        "to_order": 0,
        "supplier": "ICE_CREAM"
    },
    {
        "name": "PISTACHO",
        "current_stock": 0,
        "unit": "galones",
        "to_order": 0,
        "supplier": "ICE_CREAM"
    },
    # Packaging Supplies
    {
        "name": "TRAY BANDEJAS INDIVIDUAL",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "PACKAGING"
    },
    {
        "name": "POMOS PLASTICOS 24 OZ",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "PACKAGING"
    },
    {
        "name": "POMOS PLASTICOS 32 OZ",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "PACKAGING"
    },
    {
        "name": "BOLSAS UBER 13 X7",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "PACKAGING"
    },
    {
        "name": "ROLLITOS PARA IMPRESION",
        "current_stock": 0,
        "unit": "unidades",
        "to_order": 0,
        "supplier": "PACKAGING"
    },
    {
        "name": "SEPARADOR PLASTICO",
        "current_stock": 0,
        "unit": "pack x 1000",
        "to_order": 0,
        "supplier": "PACKAGING"
    },
    {
        "name": "DELIPAPER CHURROWORLD",
        "current_stock": 0,
        "unit": "pack x 1000",
        "to_order": 0,
        "supplier": "PACKAGING"
    },
    {
        "name": "VASOS DE CAFÉ",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "PACKAGING"
    },
    {
        "name": "VASOS DE HELADO",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "PACKAGING"
    },
    {
        "name": "VASOS DE MILKSHAKE",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "PACKAGING"
    },
    {
        "name": "BOLSAS BLANCAS CWCO",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "PACKAGING"
    },
    # Equipment
    {
        "name": "CRONOMETRO",
        "current_stock": 0,
        "unit": "unidades",
        "to_order": 0,
        "supplier": "EQUIPMENT"
    },
    {
        "name": "TERMOMETRO",
        "current_stock": 0,
        "unit": "unidades",
        "to_order": 0,
        "supplier": "EQUIPMENT"
    },
    # Maintenance
    {
        "name": "CARGA DE GAS SEMANAL",
        "current_stock": 0,
        "unit": "servicios",
        "to_order": 0,
        "supplier": "MAINTENANCE"
    },
    {
        "name": "ULTIMO CAMBIO DE ACEITE FECHA",
        "current_stock": 0,
        "unit": "servicios",
        "to_order": 0,
        "supplier": "MAINTENANCE"
    },
    # Additional Food Items
    {
        "name": "PAN PARA BURGER",
        "current_stock": 0,
        "unit": "pack x 12",
        "to_order": 0,
        "supplier": "FOOD_SUPPLIER"
    },
    {
        "name": "QUESO EN FETAS PARA BURGER",
        "current_stock": 0,
        "unit": "paquetes",
        "to_order": 0,
        "supplier": "FOOD_SUPPLIER"
    },
    {
        "name": "PAN PARA CHORIZOS",
        "current_stock": 0,
        "unit": "pack x 12",
        "to_order": 0,
        "supplier": "FOOD_SUPPLIER"
    },
    {
        "name": "BACON TROZOS",
        "current_stock": 0,
        "unit": "paquetes",
        "to_order": 0,
        "supplier": "FOOD_SUPPLIER"
    },
    {
        "name": "BACON FETAS",
        "current_stock": 0,
        "unit": "paquetes",
        "to_order": 0,
        "supplier": "FOOD_SUPPLIER"
    },
    # Sauces and Condiments
    {
        "name": "KETCHUP POTE",
        "current_stock": 0,
        "unit": "potes",
        "to_order": 0,
        "supplier": "CONDIMENTS"
    },
    {
        "name": "MOSTAZA POTE",
        "current_stock": 0,
        "unit": "potes",
        "to_order": 0,
        "supplier": "CONDIMENTS"
    },
    {
        "name": "MAYONESA POTE",
        "current_stock": 0,
        "unit": "potes",
        "to_order": 0,
        "supplier": "CONDIMENTS"
    },
    {
        "name": "KETCHUP EN SOBRES",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "CONDIMENTS"
    },
    {
        "name": "MOSTAZA EN SOBRES",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "CONDIMENTS"
    },
    {
        "name": "MAYONESA EN SOBRES",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "CONDIMENTS"
    },
    # Basic Ingredients
    {
        "name": "ACEITE",
        "current_stock": 0,
        "unit": "galones",
        "to_order": 0,
        "supplier": "BASIC_SUPPLIES"
    },
    {
        "name": "HARINA",
        "current_stock": 0,
        "unit": "libras",
        "to_order": 0,
        "supplier": "BASIC_SUPPLIES"
    },
    {
        "name": "LECHE EN POLVO",
        "current_stock": 0,
        "unit": "libras",
        "to_order": 0,
        "supplier": "BASIC_SUPPLIES"
    },
    {
        "name": "SAL 25 LB",
        "current_stock": 0,
        "unit": "bolsas",
        "to_order": 0,
        "supplier": "BASIC_SUPPLIES"
    },
    {
        "name": "SAL SOBRES",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "BASIC_SUPPLIES"
    },
    {
        "name": "AZUCAR SOBRES",
        "current_stock": 0,
        "unit": "pack x 100",
        "to_order": 0,
        "supplier": "BASIC_SUPPLIES"
    }
]

# Initialize database variables
client = None
db = None

# Get MongoDB connection string
MONGODB_URL = os.getenv("MONGODB_URL")

if not MONGODB_URL:
    raise ValueError("MONGODB_URL environment variable is not set")

client = AsyncIOMotorClient(
    MONGODB_URL,
    server_api=ServerApi('1'),
    serverSelectionTimeoutMS=5000
)

db = client.crm_leandro

async def get_db():
    try:
        await client.admin.command('ping')
        logger.info("Successfully connected to MongoDB Atlas!")
        return db
    except Exception as e:
        logger.error(f"Unable to connect to database: {e}")
        raise e

async def close_db_connection():
    client.close()

# Export only what's needed
__all__ = ['db', 'get_db', 'close_db_connection']