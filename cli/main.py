import typer

from brain.model import generate_response

app = typer.Typer()

@app.command()
def chat():

    print("🤖 Zoe v1")
    print("Type 'exit' to quit.\n")

    while True:

        user = input("You: ")

        if user.lower() in ["exit", "quit"]:
            break

        reply = generate_response(user)

        print(f"\nZoe: {reply}\n")

@app.command()
def train():
    print("Training will be added later.")

@app.command()
def ingest():
    print("PDF ingestion coming soon.")

if __name__ == "__main__":
    app()
