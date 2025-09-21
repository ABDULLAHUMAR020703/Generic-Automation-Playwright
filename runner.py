#!/usr/bin/env python3
"""
Web Automation Recipe Runner with minimal Tkinter UI
"""

import json
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from playwright.async_api import async_playwright


class RecipeRunnerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Recipe Runner")
        self.root.geometry("600x400")

        self.recipes = {}
        self.load_recipes()

        # UI: Recipe dropdown
        self.recipe_var = tk.StringVar()
        self.recipe_dropdown = ttk.Combobox(
            root, textvariable=self.recipe_var, values=list(self.recipes.keys()), state="readonly"
        )
        self.recipe_dropdown.pack(pady=10, fill="x", padx=20)

        # Buttons
        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)
        ttk.Button(button_frame, text="Reload", command=self.load_recipes).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Run", command=self.run_selected_recipe).pack(side="left", padx=5)

        # Log area
        self.log_area = scrolledtext.ScrolledText(root, wrap="word", height=15)
        self.log_area.pack(fill="both", expand=True, padx=20, pady=10)

    def log(self, message: str):
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")

    def load_recipes(self):
        recipes_file = Path("recipes.json")
        if not recipes_file.exists():
            self.recipes = {}
            self.recipe_dropdown["values"] = []
            messagebox.showwarning("No recipes", "No recipes.json file found.")
            return

        try:
            with open(recipes_file, "r") as f:
                data = json.load(f)
                self.recipes = {r["name"]: r for r in data.get("recipes", [])}
                self.recipe_dropdown["values"] = list(self.recipes.keys())
                self.log(f"Loaded {len(self.recipes)} recipes")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load recipes: {e}")

    def run_selected_recipe(self):
        name = self.recipe_var.get()
        if not name:
            messagebox.showinfo("Select Recipe", "Please select a recipe to run.")
            return
        recipe = self.recipes[name]

        # Collect overrides if there are fill steps
        inputs = {}
        fill_steps = [s for s in recipe["steps"] if s["action"] == "fill"]
        if fill_steps:
            inputs = self.ask_for_inputs(fill_steps)

        # Run in separate thread to not block Tkinter
        threading.Thread(target=lambda: asyncio.run(self.run_recipe(recipe, inputs)), daemon=True).start()

    def ask_for_inputs(self, fill_steps):
        """Open a popup dialog with entry fields for fill steps"""
        popup = tk.Toplevel(self.root)
        popup.title("Enter Inputs")
        entries = {}

        for i, step in enumerate(fill_steps):
            selector = step["selector"]
            recorded_value = step.get("value", "")
            tk.Label(popup, text=selector).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            entry = tk.Entry(popup, width=40)
            entry.insert(0, recorded_value)
            entry.grid(row=i, column=1, padx=5, pady=2)
            entries[selector] = entry

        result = {}

        def on_ok():
            for selector, entry in entries.items():
                result[selector] = entry.get()
            popup.destroy()

        tk.Button(popup, text="Run", command=on_ok).grid(row=len(fill_steps), columnspan=2, pady=10)
        popup.grab_set()
        popup.wait_window()
        return result

    async def run_recipe(self, recipe: Dict[str, Any], inputs: Dict[str, str]):
        self.log(f"🚀 Running recipe: {recipe['name']}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                for i, step in enumerate(recipe["steps"]):
                    action = step["action"]
                    self.log(f"Step {i+1}/{len(recipe['steps'])}: {action}")

                    if action == "navigate":
                        await page.goto(step["url"])
                    elif action == "click":
                        await page.click(step["selector"])
                    elif action == "fill":
                        value = inputs.get(step["selector"], step["value"])
                        await page.fill(step["selector"], value)
                    elif action == "wait":
                        await asyncio.sleep(step.get("delay", 1000) / 1000)
                    else:
                        self.log(f"⚠️ Unknown action: {action}")

                self.log("✅ Recipe finished successfully")
            except Exception as e:
                self.log(f"❌ Error: {e}")
            finally:
                await asyncio.sleep(3)
                await browser.close()


def main():
    root = tk.Tk()
    app = RecipeRunnerUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
