import pymongo
client = pymongo.MongoClient('mongodb+srv://mutawallynawwar:7WAjgvIb4egLmTEV@cluster0.mrgy4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client.compfest
userCollection = db["user"]
vacancyCollection = db["vacancy"]
questionCollection = db["question"]
frameCollection = db["frame"]
audioCollection = db["audio"]