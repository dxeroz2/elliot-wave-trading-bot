import os
import requests
import json
import sys
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

class ElliotAIAssistant:
    """A standalone AI Assistant that can read project files and troubleshoot code."""
    
    def __init__(self):
        # Configuration
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "meta-llama/llama-3-8b-instruct:free"
        
        # Keys should be provided via environment variables for security
        self.openrouter_key = os.getenv('OPENROUTER_API_KEY', '')
        
        # System Prompt
        self.system_prompt = """
        You are 'Elliot-AI', a specialized Trading Bot Assistant. 
        Analyze the provided code snippets and troubleshoot errors in the Elliot Wave Trading Bot.
        """

    def get_file_content(self, filename, max_chars=3000):
        try:
            if not os.path.exists(filename):
                return f"Error: File '{filename}' not found."
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content) > max_chars:
                    half = max_chars // 2
                    return content[:half] + "\n\n... [TRUNCATED] ...\n\n" + content[-half:]
                return content
        except Exception as e:
            return f"Error reading file: {e}"

    def ask_ai(self, user_input, context_files=None):
        full_context = ""
        if context_files:
            for f in context_files:
                content = self.get_file_content(f, max_chars=3000)
                full_context += f"\n--- File: {f} ---\n{content}\n"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Context Files:\n{full_context}\n\nUser Question: {user_input}"}
        ]

        try:
            console.print("[cyan]Contacting AI Assistant...[/cyan]")
            headers = {
                "Content-Type": "application/json",
                "X-Title": "Elliot-AI"
            }
            if self.openrouter_key:
                headers["Authorization"] = f"Bearer {self.openrouter_key}"
            
            resp = requests.post(
                self.openrouter_url,
                headers=headers,
                json={"model": self.model, "messages": messages},
                timeout=20
            )
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            else:
                return f"AI Service error (Status {resp.status_code}). Please check your API key."
        except Exception as e:
            return f"Connection failed: {e}"

    def run(self):
        console.print(Panel.fit(
            "[bold green]WELCOME TO ELLIOT-AI ASSISTANT[/bold green]\n"
            "[dim]The Specialized Elliot Wave Trading Bot Troubleshooter[/dim]",
            border_style="green"
        ))
        
        while True:
            console.print("\n[bold]What can I help you with?[/bold]")
            user_query = Prompt.ask("Query")
            if user_query.lower() in ['exit', 'quit']:
                break

            files_to_read = []
            words = user_query.lower().split()
            for word in words:
                if word.endswith(('.py', '.js', '.html', '.css', '.json')) and os.path.exists(word):
                    files_to_read.append(word)

            if files_to_read:
                console.print(f"[bold yellow]Reading context from: {', '.join(files_to_read)}[/bold yellow]")

            with console.status("[bold green]Thinking...[/bold green]"):
                response = self.ask_ai(user_query, files_to_read)
            
            console.print("\n" + "-"*50)
            console.print(Markdown(response))
            console.print("-"*50 + "\n")

if __name__ == "__main__":
    assistant = ElliotAIAssistant()
    assistant.run()
