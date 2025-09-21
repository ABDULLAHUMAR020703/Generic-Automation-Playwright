#!/usr/bin/env python3
"""
Web Automation Recipe Recorder
Records user interactions and saves them as a JSON recipe.
Now supports inserting "prompt" steps manually during recording.
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from playwright.async_api import async_playwright, Page

console = Console()


class RecipeRecorder:
    def __init__(self):
        self.steps = []
        self.recipe_name = ""
        self.description = ""
        self._last_fill_for_selector = {}  # live deduplication

    async def start_recording(self, recipe_name: str, description: str = ""):
        """Start recording a new recipe"""
        self.recipe_name = recipe_name
        self.description = description
        self.steps = []
        self._last_fill_for_selector = {}

        console.print(f"[green]🔴 Recording recipe: {recipe_name}[/green]")
        console.print("[yellow]Instructions:[/yellow]")
        console.print("• Navigate and interact with the webpage normally")
        console.print("• Type 'stop' in console to finish recording")
        console.print("• Type ':prompt Your message' to insert a prompt step")
        console.print("• Use placeholders like {name}, {email} for dynamic data")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            # Set up event listeners
            await self._setup_listeners(page)

            # Navigate to starting URL
            start_url = Prompt.ask("Enter starting URL")
            await page.goto(start_url)

            self._add_step("navigate", {"url": start_url})

            console.print("[cyan]Browser opened. Interact with the page, then type 'stop' or ':prompt ...' to continue.[/cyan]")

            # Wait for user to stop or insert prompt
            while True:
                try:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, input, "Type 'stop' or ':prompt message': "
                    )
                    if user_input.lower() == 'stop':
                        break
                    elif user_input.startswith(":prompt"):
                        message = user_input[len(":prompt"):].strip() or "Enter value"
                        self._add_step("prompt", {"message": message})
                        console.print(f"[magenta]🛑 Added prompt step: {message}[/magenta]")
                except KeyboardInterrupt:
                    break

            await browser.close()
            await self._save_recipe()

    async def _setup_listeners(self, page: Page):
        """Set up event listeners to capture interactions"""

        # Click events
        await page.expose_function("recordClick", lambda selector, text:
                                   self._add_step("click", {"selector": selector, "text": text}))

        # Input events
        await page.expose_function("recordInput", lambda selector, value:
                                   self._add_step("fill", {"selector": selector, "value": value}))

        # Navigation events
        page.on("framenavigated", lambda frame:
                self._add_step("navigate", {"url": frame.url}) if frame == page.main_frame else None)

        # Inject event tracking script with unique selector logic
        await page.add_init_script("""
            function getUniqueSelector(el) {
                if (!el) return null;

                // 1. ID
                if (el.id && document.querySelectorAll(`#${CSS.escape(el.id)}`).length === 1) {
                    return `#${CSS.escape(el.id)}`;
                }

                // 2. Name
                if (el.name && document.querySelectorAll(`[name="${el.name}"]`).length === 1) {
                    return `[name="${el.name}"]`;
                }

                // 3. aria-label
                const aria = el.getAttribute("aria-label");
                if (aria && document.querySelectorAll(`[aria-label="${aria}"]`).length === 1) {
                    return `[aria-label="${aria}"]`;
                }

                // 4. Placeholder
                const placeholder = el.getAttribute("placeholder");
                if (placeholder && document.querySelectorAll(`[placeholder="${placeholder}"]`).length === 1) {
                    return `[placeholder="${placeholder}"]`;
                }

                // 5. Class subset
                if (el.className) {
                    const classes = el.className.split(/\\s+/).slice(0, 3).map(c => `.${CSS.escape(c)}`).join('');
                    if (classes) {
                        const tag = el.tagName.toLowerCase();
                        const selector = `${tag}${classes}`;
                        if (document.querySelectorAll(selector).length === 1) {
                            return selector;
                        }
                    }
                }

                // 6. Recursive parent chain
                if (el.parentElement) {
                    const parentSelector = getUniqueSelector(el.parentElement);
                    if (parentSelector) {
                        const children = Array.from(el.parentElement.children);
                        const index = children.indexOf(el) + 1;
                        return `${parentSelector} > ${el.tagName.toLowerCase()}:nth-child(${index})`;
                    }
                }

                // 7. Fallback: tag
                return el.tagName.toLowerCase();
            }

            // Track clicks
            document.addEventListener('click', (e) => {
                const element = e.target;
                const selector = getUniqueSelector(element);
                const text = element.textContent?.trim() || element.value || '';
                window.recordClick(selector, text);
            });

            // Track input changes
            document.addEventListener('input', (e) => {
                const element = e.target;
                const selector = getUniqueSelector(element);
                const value = element.value;
                window.recordInput(selector, value);
            });
        """)

    def _add_step(self, action: str, data: dict):
        """Add a step to the recipe (with live dedup for fills)"""
        step = {
            "action": action,
            "timestamp": datetime.now().isoformat(),
            **data
        }

        if action == "fill":
            selector = data["selector"]
            # Deduplicate live: replace last fill for same selector
            self._last_fill_for_selector[selector] = step
            console.print(f"[blue]📝 Updated fill: {selector} → {data['value']}[/blue]")
        else:
            # Flush pending fills before any non-fill action
            for s in self._last_fill_for_selector.values():
                self.steps.append(s)
            self._last_fill_for_selector = {}
            self.steps.append(step)
            console.print(f"[blue]📝 Recorded: {action} - {data}[/blue]")

    async def _save_recipe(self):
        """Save the recorded recipe to JSON file"""
        # Flush any remaining fills
        for s in self._last_fill_for_selector.values():
            self.steps.append(s)
        self._last_fill_for_selector = {}

        # Collapse fills again just in case
        collapsed_steps = self._collapse_fills(self.steps)

        recipe = {
            "name": self.recipe_name,
            "description": self.description,
            "created": datetime.now().isoformat(),
            "steps": collapsed_steps,
            "placeholders": self._extract_placeholders(collapsed_steps)
        }

        recipes_file = Path("recipes.json")
        recipes = {"recipes": []}

        if recipes_file.exists():
            try:
                with open(recipes_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        recipes = json.loads(content)
            except (json.JSONDecodeError, OSError):
                console.print("[red]⚠️ Warning: recipes.json was empty or invalid. Reinitializing...[/red]")
                recipes = {"recipes": []}

        recipes["recipes"].append(recipe)

        with open(recipes_file, 'w') as f:
            json.dump(recipes, f, indent=2)

        console.print(f"[green]✅ Recipe '{self.recipe_name}' saved successfully![/green]")
        console.print(f"[cyan]Total steps recorded: {len(collapsed_steps)} (reduced from {len(self.steps)})[/cyan]")

    def _collapse_fills(self, steps):
        """Collapse multiple fill actions on the same selector into the last one"""
        collapsed = []
        last_fills = {}

        for step in steps:
            if step["action"] == "fill":
                last_fills[step["selector"]] = step
            else:
                collapsed.extend(last_fills.values())
                last_fills = {}
                collapsed.append(step)

        collapsed.extend(last_fills.values())
        return collapsed

    def _extract_placeholders(self, steps: list) -> list:
        """Extract placeholder variables from recorded steps"""
        placeholders = set()

        for step in steps:
            if "value" in step and isinstance(step["value"], str):
                import re
                matches = re.findall(r'\{([^}]+)\}', step["value"])
                placeholders.update(matches)

        return list(placeholders)


async def main():
    console.print("[bold green]🎬 Web Automation Recipe Recorder[/bold green]")

    recorder = RecipeRecorder()

    recipe_name = Prompt.ask("Enter recipe name")
    description = Prompt.ask("Enter description (optional)", default="")

    await recorder.start_recording(recipe_name, description)


if __name__ == "__main__":
    asyncio.run(main())
