# Agent Basics

An agent is a software system that can observe context, decide what action to take, use tools when needed, and continue until it reaches a stopping condition.

In a simple learning project, the agent loop usually contains four steps:

1. Read the user task and current session messages.
2. Ask the language model for either a final answer or a tool call.
3. Execute the selected tool and record the observation.
4. Repeat until the model returns a final answer or the loop reaches max steps.

Good agent implementations make each step visible through traces and eval cases.