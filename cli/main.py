import typer

app = typer.Typer()

@app.command()
def chat():
    print("Hello. I am Zoe.")

@app.command()
def train():
    print("Training will be added later.")

@app.command()
def ingest():
    print("PDF ingestion coming soon.")

if __name__ == "__main__":
    app()
