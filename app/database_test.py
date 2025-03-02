from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def test_connection():
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.crm_leandro
        
        # Test the connection
        await client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        
        # Check schedules collection
        schedules = await db.schedules.find().to_list(1000)
        print("\nSchedules found:", len(schedules))
        
        # Print each schedule
        for schedule in schedules:
            print(f"\nEmployee: {schedule.get('employee')}")
            print(f"Color: {schedule.get('background_color')}")
            print("Schedule:")
            for day, times in schedule.get('weekly_schedule', {}).items():
                print(f"  {day}: {times}")
                
    except Exception as e:
        print("❌ Error:", str(e))
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_connection())