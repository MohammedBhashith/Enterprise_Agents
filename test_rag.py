from rag import answer_policy_question

print("HR Policy Test")
print(answer_policy_question("EMP001", "What is the notice period policy?"))

print("\n" + "-" * 50 + "\n")

print("IT Policy Test")
print(answer_policy_question("EMP001", "What is the asset approval flow?"))