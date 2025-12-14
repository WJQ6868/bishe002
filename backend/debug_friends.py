"""
Debug script to test friend list retrieval
"""
import asyncio
from sqlalchemy import select, or_
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.friend import Friendship

async def debug_contacts():
    # Test for user 1087 (student 20230001)
    user_id = 1087
    
    async with AsyncSessionLocal() as db:
        # Get user
        user_stmt = select(User).where(User.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalars().first()
        print(f"Testing for user: {user.id} - {user.username} - {user.role}")
        
        # Get friendships
        friendship_stmt = select(Friendship).where(
            or_(
                Friendship.user_id_1 == user.id,
                Friendship.user_id_2 == user.id
            )
        )
        friendship_result = await db.execute(friendship_stmt)
        friendships = friendship_result.scalars().all()
        
        print(f"\nFound {len(friendships)} friendships:")
        contact_user_ids = set()
        for friendship in friendships:
            print(f"  Friendship ID {friendship.id}: user_{friendship.user_id_1} <-> user_{friendship.user_id_2}")
            friend_id = friendship.get_friend_id(user.id)
            if friend_id:
                contact_user_ids.add(friend_id)
                print(f"    -> Friend ID: {friend_id}")
        
        print(f"\nContact user IDs: {contact_user_ids}")
        
        # Get friend details
        if contact_user_ids:
            friend_stmt = select(User).where(User.id.in_(contact_user_ids))
            friend_result = await db.execute(friend_stmt)
            friends = friend_result.scalars().all()
            print(f"\nFriend details:")
            for friend in friends:
                print(f"  ID={friend.id}, username={friend.username}, role={friend.role}")

if __name__ == "__main__":
    asyncio.run(debug_contacts())
