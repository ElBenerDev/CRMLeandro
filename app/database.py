from motor.motor_asyncio import AsyncIOMotorClient
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

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

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient("mongodb://localhost:27017")
        self.db = self.client.crm_leandro
        
        # Initialize collections
        self.inventory = self.db.inventory
        self.stock_movements = self.db.stock_movements
        self.users = self.db.users
        self.schedules = self.db.schedules
        self.daily_cash = self.db.daily_cash

    async def initialize(self):
        try:
            # Test connection
            await self.db.command("ping")
            logger.info("Connected to MongoDB")

            # Get list of collections properly
            collections_cursor = await self.db.list_collections()
            collections = []
            async for collection in collections_cursor:
                collections.append(collection["name"])
            logger.info(f"Found collections: {collections}")
            
            # Create stock_movements if doesn't exist
            if 'stock_movements' not in collections:
                await self.db.create_collection("stock_movements")
                await self.stock_movements.create_index(
                    [("item_id", 1), ("timestamp", -1)],
                    name="item_id_1_timestamp_-1"
                )
                logger.info("Created stock_movements collection and index")

            # Initialize inventory if empty
            inventory_count = await self.inventory.count_documents({})
            if inventory_count == 0:
                result = await self.inventory.insert_many(DEFAULT_INVENTORY)
                logger.info(f"Initialized inventory with {len(result.inserted_ids)} items")

            # Create indexes
            await self.inventory.create_index("name", unique=True)
            await self.users.create_index("username", unique=True)
            
            logger.info("Database initialization complete")
            return True

        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            return False

    async def reset_inventory(self):
        try:
            await self.inventory.drop()
            await self.inventory.insert_many(DEFAULT_INVENTORY)
            logger.info(f"Reset inventory with {len(DEFAULT_INVENTORY)} items")
            return True
        except Exception as e:
            logger.error(f"Error resetting inventory: {e}")
            return False

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection")

# Create global database instance
db = Database()

async def init_db():
    return await db.initialize()

# Export database instance and initialization function
__all__ = ['db', 'init_db']