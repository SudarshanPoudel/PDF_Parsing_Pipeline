from fastapi import FastAPI
from routers.pdf_parsing_router import paf_parsing_router
import uvicorn

import sys
sys.path.append("..") 

app = FastAPI()
app.include_router(paf_parsing_router)

if __name__ == '__main__':
    uvicorn.run("main:app", reload=False)
