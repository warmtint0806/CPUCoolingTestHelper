from fastapi import FastAPI, Form

app = FastAPI()

@app.post("/api/tp")
def read_data(h: float = Form(...), t: float = Form(...), f: float = Form(...)):
    # For the sake of demonstration, just echoing back the received data.
    return {
        "received_h": h,
        "received_t": t,
        "received_f": f,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
