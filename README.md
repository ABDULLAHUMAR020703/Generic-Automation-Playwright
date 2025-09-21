# 🌀 Web Automation Recipe MVP with Playwright

A simple web automation tool that records user interactions and replays them with dynamic data.

## 🚀 Quick Start

1. **Setup** (Already completed)
   ```bash
   # Activate virtual environment
   venv\Scripts\Activate.ps1
   ```

2. **Create a sample recipe**
   ```bash
   python demo.py
   ```

3. **Record your own recipe**
   ```bash
   python recorder.py
   ```

4. **Run a recipe**
   ```bash
   python runner.py
   ```

## 📁 Project Structure

- `recorder.py` - Records web interactions and saves as JSON recipes
- `runner.py` - Executes saved recipes with user inputs
- `recipes.json` - Stores all recorded recipes
- `demo.py` - Creates sample recipes for testing

## 🎬 Recording Recipes

Run `python recorder.py` and follow these steps:

1. Enter a recipe name (e.g., "login_form")
2. Enter an optional description
3. Provide the starting URL
4. A Chrome browser will open - interact with the webpage normally
5. Use placeholders like `{username}`, `{email}` for dynamic data
6. Type 'stop' in the console when done

### Supported Actions
- **Navigate** - Go to URLs
- **Click** - Click buttons, links, etc.
- **Fill** - Fill form inputs
- **Wait** - Add delays between actions

## 🎮 Running Recipes

Run `python runner.py` for interactive mode, or specify a recipe:

```bash
python runner.py google_search
```

### Interactive Commands
- `list` - Show all available recipes
- `run <recipe_name>` - Execute a specific recipe
- `reload` - Reload recipes from file
- `quit` - Exit the program

## 🔧 Recipe Format

Recipes are stored as JSON with this structure:

```json
{
  "name": "my_recipe",
  "description": "Description of what this recipe does",
  "created": "2024-01-01T12:00:00",
  "steps": [
    {
      "action": "navigate",
      "url": "https://example.com",
      "timestamp": "..."
    },
    {
      "action": "fill",
      "selector": "#email",
      "value": "{user_email}",
      "timestamp": "..."
    },
    {
      "action": "click",
      "selector": "button[type='submit']",
      "text": "Submit",
      "timestamp": "..."
    }
  ],
  "placeholders": ["user_email"]
}
```

## 🎯 Use Cases

- **Form Automation** - Fill out repetitive forms with different data
- **Testing** - Automated testing of web workflows
- **Data Entry** - Bulk data entry tasks
- **Web Scraping** - Navigate and extract data from websites

## ⚠️ Notes

- Only works with Chrome/Chromium browser
- Recorded selectors might break if website structure changes
- Use unique IDs and classes for more reliable selectors
- Test your recipes after recording to ensure they work correctly

## 🔍 Troubleshooting

- **Recipe not found**: Make sure the recipe name matches exactly
- **Element not found**: The website might have changed - re-record the recipe
- **Slow execution**: Increase wait times between steps if needed
