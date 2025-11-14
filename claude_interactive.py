"""
Interactive Claude Agent Terminal
See Claude's thought process in real-time and chat with it about tokens
"""
import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.live import Live
from rich.table import Table
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from config.settings import Settings


class InteractiveClaude:
    """Interactive Claude agent with conversation and analysis modes"""

    def __init__(self):
        self.console = Console()
        self.settings = Settings()
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        self.model = "claude-3-haiku-20240307"
        self.conversation_history = []
        self.results_dir = Path("data/results")

    def print_header(self):
        """Print welcome header"""
        header = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║      🤖 Claude Interactive Trading Agent Terminal        ║
║                                                           ║
║  Talk to Claude about token analysis and trading         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        self.console.print(header, style="bold cyan")

    def load_latest_analysis(self) -> Optional[Dict[str, Any]]:
        """Load the most recent token analysis"""
        if not self.results_dir.exists():
            return None

        json_files = sorted(self.results_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

        if not json_files:
            return None

        with open(json_files[0], 'r') as f:
            return json.load(f)

    def display_analysis(self, analysis: Dict[str, Any]):
        """Display token analysis in a nice format"""
        token = analysis.get('token_address', 'Unknown')[:16] + "..."

        # Create summary table
        table = Table(title=f"📊 Token Analysis: {token}", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        claude_data = analysis.get('claude_analysis', {})

        table.add_row("Recommendation", claude_data.get('recommendation', 'N/A'))
        table.add_row("Confidence", claude_data.get('confidence', 'N/A'))
        table.add_row("Risk Score", f"{claude_data.get('risk_score', 'N/A')}/10")

        prediction = analysis.get('prediction', {})
        table.add_row("ML Prediction", f"{prediction.get('prediction', 0)*100:.1f}%")

        self.console.print(table)

        # Display Claude's reasoning
        raw_response = claude_data.get('raw_text', claude_data.get('raw_response', ''))
        if raw_response:
            self.console.print("\n")
            self.console.print(Panel(
                Markdown(raw_response),
                title="🧠 Claude's Analysis",
                border_style="green"
            ))

    def chat_mode(self, initial_context: Optional[Dict] = None):
        """Interactive chat mode with Claude"""
        self.console.print("\n[bold green]💬 Chat Mode Activated[/bold green]")
        self.console.print("[dim]Type 'exit' to quit, 'clear' to clear history, 'analyze' to review latest token[/dim]\n")

        # Add initial context if available
        if initial_context:
            context_msg = f"""You are analyzing Solana pump.fun tokens.

Latest token analysis available:
Token: {initial_context.get('token_address', 'Unknown')[:16]}...
Recommendation: {initial_context.get('claude_analysis', {}).get('recommendation', 'N/A')}
Risk Score: {initial_context.get('claude_analysis', {}).get('risk_score', 'N/A')}/10

The user can ask you questions about this token or trading strategy in general.
Be conversational, insightful, and explain your reasoning clearly.
"""
            self.conversation_history.append({
                "role": "user",
                "content": context_msg
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": "I'm ready to discuss this token analysis or any trading questions you have!"
            })

        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]")

                if user_input.lower() == 'exit':
                    self.console.print("[yellow]👋 Goodbye![/yellow]")
                    break
                elif user_input.lower() == 'clear':
                    self.conversation_history = []
                    self.console.print("[green]✓ History cleared[/green]")
                    continue
                elif user_input.lower() == 'analyze':
                    latest = self.load_latest_analysis()
                    if latest:
                        self.display_analysis(latest)
                    else:
                        self.console.print("[red]No analysis found[/red]")
                    continue

                # Add to history
                self.conversation_history.append({
                    "role": "user",
                    "content": user_input
                })

                # Show thinking indicator
                with self.console.status("[bold cyan]🤔 Claude is thinking...", spinner="dots"):
                    # Call Claude
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=2000,
                        temperature=0.7,
                        messages=self.conversation_history
                    )

                    assistant_response = response.content[0].text

                # Display response
                self.console.print("\n[bold green]Claude[/bold green]:")
                self.console.print(Panel(Markdown(assistant_response), border_style="green"))

                # Add to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_response
                })

            except KeyboardInterrupt:
                self.console.print("\n[yellow]👋 Goodbye![/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")

    def watch_mode(self):
        """Watch mode - stream Claude's analysis as it happens"""
        self.console.print("\n[bold green]👀 Watch Mode - Monitoring for new analyses...[/bold green]")
        self.console.print("[dim]Press Ctrl+C to exit[/dim]\n")

        last_file = None

        try:
            while True:
                # Check for new analysis files
                json_files = sorted(self.results_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

                if json_files and (last_file is None or json_files[0] != last_file):
                    last_file = json_files[0]

                    with open(last_file, 'r') as f:
                        analysis = json.load(f)

                    self.console.print(f"\n[bold cyan]🔔 New Analysis Detected: {datetime.now().strftime('%H:%M:%S')}[/bold cyan]")
                    self.display_analysis(analysis)
                    self.console.print("\n" + "="*60 + "\n")

                import time
                time.sleep(5)  # Check every 5 seconds

        except KeyboardInterrupt:
            self.console.print("\n[yellow]👋 Exiting watch mode[/yellow]")

    def run(self):
        """Main interactive loop"""
        self.print_header()

        # Show menu
        self.console.print("\n[bold]Choose a mode:[/bold]")
        self.console.print("1. 💬 Chat Mode - Talk to Claude about trading")
        self.console.print("2. 📊 Analyze Latest Token - Review most recent analysis")
        self.console.print("3. 👀 Watch Mode - Monitor live analyses")
        self.console.print("4. 🚪 Exit\n")

        choice = Prompt.ask("Select option", choices=["1", "2", "3", "4"], default="1")

        if choice == "1":
            # Load latest for context
            latest = self.load_latest_analysis()
            self.chat_mode(initial_context=latest)
        elif choice == "2":
            latest = self.load_latest_analysis()
            if latest:
                self.display_analysis(latest)
                # Ask if they want to chat about it
                if Prompt.ask("\n💬 Want to discuss this analysis?", choices=["y", "n"], default="y") == "y":
                    self.chat_mode(initial_context=latest)
            else:
                self.console.print("[red]No analysis found. Run main.py first![/red]")
        elif choice == "3":
            self.watch_mode()
        else:
            self.console.print("[yellow]👋 Goodbye![/yellow]")


def main():
    """Entry point"""
    interactive = InteractiveClaude()
    interactive.run()


if __name__ == "__main__":
    main()
