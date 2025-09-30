# Meal Lab

A modern web application for optimizing weekly meal plans based on nutritional requirements.

## Features

- **File Upload**: Upload JSON files containing meal options and their nutritional content
- **Nutritional Requirements**: Set minimum and maximum limits for various nutrients
- **Meal Plan Generation**: Generate optimized weekly meal plans
- **Modern UI**: Clean black and white design using Tailwind CSS

## Setup Instructions

1. **Create and Activate Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**:
   ```bash
   python app.py
   ```

4. **Access the Application**:
   Open your browser and go to `http://localhost:5001`

## Usage

1. **Upload Meal Data**: Upload a JSON file containing your meal options with nutritional information
2. **Set Requirements**: Configure your minimum and maximum nutritional requirements
3. **Generate Plan**: Click "Create Meal Plan" to generate your weekly meal plan
4. **View Results**: Review your optimized meal plan for the week

## JSON File Format

Your meal data JSON file should contain an array of meal objects with the following structure:

```json
[
  {
    "title": "Classic Italian Margherita Pizza",
    "description": "Thin crust topped with fresh tomato sauce, mozzarella cheese, and basil leaves.",
    "estimated_cost_usd": 8.0,
    "calories": 250,
    "macros": {
      "protein": 10,
      "carbs": 30,
      "fat": 10
    },
    "micros": {
      "vitamin_a_mcg": 200,
      "vitamin_c_mg": 10,
      "vitamin_d_mcg": 0,
      "vitamin_e_mg": 1,
      "calcium_mg": 200,
      "iron_mg": 1.5,
      "magnesium_mg": 20,
      "potassium_mg": 250,
      "sodium_mg": 400,
      "zinc_mg": 1
    }
  }
]
```

## Nutritional Fields

### Basic Information
- `title`: Name of the meal
- `description`: Description of the meal
- `estimated_cost_usd`: Estimated cost in USD
- `calories`: Energy content in calories

### Macronutrients (macros)
- `protein`: Protein content in grams
- `carbs`: Carbohydrate content in grams
- `fat`: Fat content in grams

### Micronutrients (micros)
- `vitamin_a_mcg`: Vitamin A in micrograms
- `vitamin_c_mg`: Vitamin C in milligrams
- `vitamin_d_mcg`: Vitamin D in micrograms
- `vitamin_e_mg`: Vitamin E in milligrams
- `calcium_mg`: Calcium in milligrams
- `iron_mg`: Iron in milligrams
- `magnesium_mg`: Magnesium in milligrams
- `potassium_mg`: Potassium in milligrams
- `sodium_mg`: Sodium in milligrams
- `zinc_mg`: Zinc in milligrams

## Development

The application uses:
- **Backend**: Python Flask
- **Frontend**: HTML with Tailwind CSS
- **File Upload**: Werkzeug for secure file handling
- **Algorithm**: Basic meal selection (can be enhanced with optimization algorithms)

## Future Enhancements

- Advanced optimization algorithms (linear programming, genetic algorithms)
- User authentication and meal plan history
- Recipe integration
- Shopping list generation
- Nutritional analysis and reporting
