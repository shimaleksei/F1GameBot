"""Simple test script to verify bot functionality."""
import asyncio
from database import init_db, User, Race, Driver, Bet, RaceResult, PointsPerRace
from services.user_service import get_or_create_user, get_user_by_telegram_id
from services.race_service import get_all_races, create_race, get_race_by_id
from services.driver_service import get_all_drivers
from services.bet_service import create_or_update_bet, get_bet, is_betting_open
from services.result_service import create_or_update_result, calculate_and_save_points
from services.scoring_service import get_leaderboard, get_user_total_points
from config import validate_config


async def test_database():
    """Test database initialization."""
    print("1. Testing database initialization...")
    await init_db()
    print("   ✓ Database initialized")
    
    drivers = await get_all_drivers()
    print(f"   ✓ Found {len(drivers)} drivers in database")
    if drivers:
        print(f"   ✓ Sample driver: {drivers[0].code} - {drivers[0].full_name}")


async def test_user_service():
    """Test user service."""
    print("\n2. Testing user service...")
    test_telegram_id = 123456789
    user = await get_or_create_user(
        telegram_id=test_telegram_id,
        username="test_user",
        full_name="Test User"
    )
    print(f"   ✓ User created/retrieved: {user.full_name} (ID: {user.id})")
    
    user2 = await get_user_by_telegram_id(test_telegram_id)
    assert user2.id == user.id, "User retrieval failed"
    print("   ✓ User retrieval works")


async def test_race_service():
    """Test race service."""
    print("\n3. Testing race service...")
    race = await create_race(
        name="Test Grand Prix",
        date="2025-12-25",
        start_time="15:00",
        timezone="UTC"
    )
    print(f"   ✓ Race created: {race.name} (ID: {race.id})")
    
    races = await get_all_races()
    print(f"   ✓ Found {len(races)} race(s) in database")
    
    race2 = await get_race_by_id(race.id)
    assert race2.id == race.id, "Race retrieval failed"
    print("   ✓ Race retrieval works")


async def test_bet_service():
    """Test bet service."""
    print("\n4. Testing bet service...")
    user = await get_user_by_telegram_id(123456789)
    races = await get_all_races()
    
    if races:
        race = races[0]
        # Check if betting is open
        is_open = is_betting_open(race.date, race.start_time, race.timezone)
        print(f"   ✓ Betting status check: {'Open' if is_open else 'Closed'}")
        
        # Create a test bet
        bet = await create_or_update_bet(
            user_id=user.id,
            race_id=race.id,
            driver_1st="VER",
            driver_2nd="HAM",
            driver_3rd="LEC"
        )
        print(f"   ✓ Bet created: {bet.driver_1st}, {bet.driver_2nd}, {bet.driver_3rd}")
        
        bet2 = await get_bet(user.id, race.id)
        assert bet2.id == bet.id, "Bet retrieval failed"
        print("   ✓ Bet retrieval works")


async def test_result_service():
    """Test result service."""
    print("\n5. Testing result service...")
    races = await get_all_races()
    
    if races:
        race = races[0]
        # Create result
        result = await create_or_update_result(
            race_id=race.id,
            driver_1st="VER",
            driver_2nd="HAM",
            driver_3rd="LEC"
        )
        print(f"   ✓ Result created: {result.driver_1st}, {result.driver_2nd}, {result.driver_3rd}")
        
        # Calculate points
        points_summary = await calculate_and_save_points(race.id, result)
        print(f"   ✓ Points calculated for {len(points_summary)} bet(s)")
        if points_summary:
            print(f"   ✓ Sample: {points_summary[0]['user_name']} got {points_summary[0]['points']} points")


async def test_scoring_service():
    """Test scoring service."""
    print("\n6. Testing scoring service...")
    user = await get_user_by_telegram_id(123456789)
    
    total_points = await get_user_total_points(user.id)
    print(f"   ✓ User total points: {total_points}")
    
    leaderboard = await get_leaderboard(limit=10)
    print(f"   ✓ Leaderboard: {len(leaderboard)} user(s)")
    if leaderboard:
        print(f"   ✓ Top user: {leaderboard[0]['full_name']} - {leaderboard[0]['total_points']} points")


async def main():
    """Run all tests."""
    print("=" * 50)
    print("F1 Game Bot - Functionality Test")
    print("=" * 50)
    
    try:
        validate_config()
        print("✓ Configuration validated\n")
        
        await test_database()
        await test_user_service()
        await test_race_service()
        await test_bet_service()
        await test_result_service()
        await test_scoring_service()
        
        print("\n" + "=" * 50)
        print("✓ All tests passed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())


