import markpy

# sample_text_file = "demoStates.txt"
sample_text_file = "demoTransitions.txt"
sample_text_file = "demo2Transitions.txt"
sample_text_file = "demoTrails.txt"

# markpy.ImportStates(sample_text_file)
# markpy.ProcessTransitions(sample_text_file)


print(markpy.predictUserClass(sample_text_file))
