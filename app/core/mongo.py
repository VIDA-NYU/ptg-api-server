import os
import motor.motor_asyncio
from bson.objectid import ObjectId

DEFAULT_MONGO_URI = os.getenv('MONGO_URL') or "mongodb://localhost:27017"


class DB:
    def __init__(self, collection, db=None, uri=None):
        self.client = client = motor.motor_asyncio.AsyncIOMotorClient(uri or DEFAULT_MONGO_URI)
        self.db = db = getattr(client, db or 'app')
        self.collection = db.get_collection(collection)

    def prepare_query(self, _id: str=None, **query):
        if _id:
            query['_id'] = _id#ObjectId(_id)
        return query

    def process(self, data):
        data['_id'] = str(data['_id'])
        return data

    async def get_all(self) -> list:
        return [self.process(d) async for d in self.collection.find()]

    async def get(self, _id: str=None, **query) -> dict:
        data = await self.collection.find_one(self.prepare_query(_id, **query))
        if data:
            return self.process(data)

    async def add(self, data: dict) -> dict:
        obj = await self.collection.insert_one(data)
        data = await self.collection.find_one({"_id": obj.inserted_id})
        return self.process(data)

    async def update(self, _id: str, data: dict) -> bool:
        if not data:
            return False
        obj = await self.collection.find_one(self.prepare_query(_id))
        if obj:
            updated = await self.collection.update_one(self.prepare_query(_id), {"$set": data})
            return bool(updated)
        return False

    async def delete(self, _id: str):
        obj = await self.collection.find_one(self.prepare_query(_id))
        if obj:
            await self.collection.delete_one(self.prepare_query(_id))
            return True
        return False
