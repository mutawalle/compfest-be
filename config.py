import pymongo
client = pymongo.MongoClient('mongodb+srv://mutawallynawwar:7WAjgvIb4egLmTEV@cluster0.mrgy4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client.compfest
userCollection = db["user"]
frameCollection = db["frame"]
audioCollection = db["audio"]