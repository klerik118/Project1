from fastapi import FastAPI



app = FastAPI()

@app.get('/health')
async def hello():
    return 'Hello guy!'