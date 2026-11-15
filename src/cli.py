from assistant import ask

print("Data assistant ready. Type a question (blank line to quit).")
while True:
    q = input("\n> ").strip()
    if not q:
        break
    print(ask(q))