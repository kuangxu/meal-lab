"""
Meal Planning Linear Optimization Problem

This module implements a linear optimization problem for weekly meal planning
using PuLP. The optimization minimizes total cost while ensuring
nutritional constraints are met.

Problem Structure:
- Decision Variables: Binary matrix X[i,j] where i=meal_index, j=day_meal_slot
- Objective: Minimize total cost across all selected meals
- Constraints: 
  1. Nutritional bounds (macro and micro nutrients)
  2. Each meal can be selected at most twice per week
  3. Non-negativity constraints
"""

import json
import numpy as np
from pulp import LpProblem, LpMinimize, LpMaximize, LpVariable, LpStatus, lpSum, value
from typing import Dict, List, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MealOptimizer:
    """
    Linear optimization solver for meal planning with nutritional constraints.
    """
    
    def __init__(self, meals_file: str = "data/meals.json", 
                 profiles_file: str = "data/nutritional_profiles.json",
                 config_file: str = "data/config.json"):
        """
        Initialize the meal optimizer with data files.
        
        Args:
            meals_file: Path to meals data JSON file
            profiles_file: Path to nutritional profiles JSON file  
            config_file: Path to configuration JSON file
        """
        self.meals_file = meals_file
        self.profiles_file = profiles_file
        self.config_file = config_file
        
        # Load data
        self.meals = self._load_meals()
        self.nutritional_profiles = self._load_nutritional_profiles()
        self.config = self._load_config()
        
        # Problem dimensions
        self.num_meals = len(self.meals)
        self.days_of_week = self.config["meal_planning"]["days_of_week"]
        self.num_days = len(self.days_of_week)
        self.meals_per_day = self.config["meal_planning"]["meals_per_day"]["max"]
        self.total_meal_slots = self.num_days * self.meals_per_day
        
        # Nutritional categories
        self.macro_nutrients = ["protein", "carbs", "fat"]
        self.micro_nutrients = [
            "vitamin_a_mcg", "vitamin_c_mg", "vitamin_d_mcg", "vitamin_e_mg",
            "calcium_mg", "iron_mg", "magnesium_mg", "potassium_mg", 
            "sodium_mg", "zinc_mg"
        ]
        self.all_nutrients = self.macro_nutrients + self.micro_nutrients
        
        logger.info(f"Initialized optimizer with {self.num_meals} meals, "
                   f"{self.num_days} days, {self.total_meal_slots} total meal slots")
    
    def _load_meals(self) -> List[Dict]:
        """Load meals data from JSON file."""
        try:
            with open(self.meals_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Meals file {self.meals_file} not found")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {self.meals_file}")
            raise
    
    def _load_nutritional_profiles(self) -> Dict:
        """Load nutritional profiles from JSON file."""
        try:
            with open(self.profiles_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Nutritional profiles file {self.profiles_file} not found")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {self.profiles_file}")
            raise
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file {self.config_file} not found")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {self.config_file}")
            raise
    
    def _get_nutrient_value(self, meal: Dict, nutrient: str) -> float:
        """
        Extract nutrient value from meal data.
        
        Args:
            meal: Meal dictionary
            nutrient: Nutrient name
            
        Returns:
            Nutrient value as float
        """
        if nutrient in ["protein", "carbs", "fat"]:
            return float(meal["macros"][nutrient])
        elif nutrient in self.micro_nutrients:
            return float(meal["micros"][nutrient])
        elif nutrient == "calories":
            return float(meal["calories"])
        else:
            raise ValueError(f"Unknown nutrient: {nutrient}")
    
    def _map_profile_nutrient(self, profile_nutrient: str) -> str:
        """
        Map nutritional profile nutrient names to meal data nutrient names.
        
        Args:
            profile_nutrient: Nutrient name from profile
            
        Returns:
            Corresponding nutrient name in meal data
        """
        mapping = {
            "vitaminA": "vitamin_a_mcg",
            "vitaminC": "vitamin_c_mg", 
            "vitaminD": "vitamin_d_mcg",
            "vitaminE": "vitamin_e_mg",
            "calcium": "calcium_mg",
            "iron": "iron_mg",
            "magnesium": "magnesium_mg",
            "potassium": "potassium_mg",
            "sodium": "sodium_mg",
            "zinc": "zinc_mg"
        }
        return mapping.get(profile_nutrient, profile_nutrient)
    
    def solve(self, profile_name: str = "healthy-adult", 
              max_meals_per_meal: int = 2, objective: str = "minimize_cost") -> Dict:
        """
        Solve the meal planning optimization problem.
        
        Args:
            profile_name: Nutritional profile to use for constraints
            max_meals_per_meal: Maximum times each meal can be selected
            
        Returns:
            Dictionary containing solution results
        """
        if profile_name not in self.nutritional_profiles:
            raise ValueError(f"Unknown profile: {profile_name}")
        
        profile = self.nutritional_profiles[profile_name]
        
        # Create problem
        if objective == "minimize_cost":
            problem = LpProblem("MealPlanning", LpMinimize)
        elif objective == "maximize_rating":
            problem = LpProblem("MealPlanning", LpMaximize)
        else:
            raise ValueError(f"Unknown objective: {objective}")
        
        # Decision variables: X[i,j] = 1 if meal i is selected for meal slot j
        # i: meal index (0 to num_meals-1)
        # j: meal slot index (0 to total_meal_slots-1)
        x = {}
        for i in range(self.num_meals):
            for j in range(self.total_meal_slots):
                x[i, j] = LpVariable(f'x_{i}_{j}', cat='Binary')
        
        logger.info(f"Created {self.num_meals * self.total_meal_slots} decision variables")
        
        # Objective: Minimize cost or maximize rating
        objective_expr = []
        for i in range(self.num_meals):
            for j in range(self.total_meal_slots):
                if objective == "minimize_cost":
                    # Minimize total cost
                    objective_expr.append(self.meals[i]["estimated_cost_usd"] * x[i, j])
                elif objective == "maximize_rating":
                    # Maximize total user rating
                    user_rating = self.meals[i].get("user_rating", 5)  # Default to 5 if not set
                    objective_expr.append(user_rating * x[i, j])
        
        problem += lpSum(objective_expr)
        
        # Constraint 1: Each meal can be selected at most max_meals_per_meal times
        for i in range(self.num_meals):
            problem += lpSum([x[i, j] for j in range(self.total_meal_slots)]) <= max_meals_per_meal
        
        # Constraint 2: Ensure we have exactly one meal per day
        for day_idx in range(self.num_days):
            # Exactly 1 meal per day
            day_vars = []
            for i in range(self.num_meals):
                for meal_slot in range(self.meals_per_day):
                    j = day_idx * self.meals_per_day + meal_slot
                    day_vars.append(x[i, j])
            problem += lpSum(day_vars) == 1
        
        # Constraint 3: Nutritional constraints on AVERAGE values
        # For each nutrient, ensure average across all selected meals falls within bounds
        # Since we have exactly 7 meals (1 per day), we can use fixed total
        total_meals = 7  # Fixed number of meals per week
        
        # Process all nutrients including calories
        nutrients_to_process = ["calories"] + self.all_nutrients
        
        for nutrient in nutrients_to_process:
            profile_nutrient = self._map_profile_nutrient(nutrient)
            
            if profile_nutrient in profile:
                min_val = profile[profile_nutrient]["min"]
                max_val = profile[profile_nutrient]["max"]
                
                logger.info(f"Setting constraints for {nutrient} (profile: {profile_nutrient}): min={min_val}, max={max_val}")
                
                # Correct approach: 
                # sum(nutrient_value * x[i,j]) >= min_val * total_meals
                # sum(nutrient_value * x[i,j]) <= max_val * total_meals
                
                # Nutritional lower bound: sum(nutrient_value * x[i,j]) >= min_val * total_meals
                # Only add lower bound constraint if min_val > 0
                if min_val > 0:
                    nutrient_expr = []
                    for i in range(self.num_meals):
                        nutrient_value = self._get_nutrient_value(self.meals[i], nutrient)
                        for j in range(self.total_meal_slots):
                            nutrient_expr.append(nutrient_value * x[i, j])
                    problem += lpSum(nutrient_expr) >= min_val * total_meals
                    logger.info(f"  Lower bound constraint: sum >= {min_val * total_meals} (avg >= {min_val})")
                else:
                    logger.info(f"  Skipping lower bound constraint (min_val = 0)")
                
                # Nutritional upper bound: sum(nutrient_value * x[i,j]) <= max_val * total_meals
                if max_val < float('inf'):
                    nutrient_expr = []
                    for i in range(self.num_meals):
                        nutrient_value = self._get_nutrient_value(self.meals[i], nutrient)
                        for j in range(self.total_meal_slots):
                            nutrient_expr.append(nutrient_value * x[i, j])
                    problem += lpSum(nutrient_expr) <= max_val * total_meals
                    logger.info(f"  Upper bound constraint: sum <= {max_val * total_meals} (avg <= {max_val})")
                else:
                    logger.info(f"  Skipping upper bound constraint (max_val = infinity)")
        
        # Constraint 4: Limit total number of meals to exactly 7 (1 per day)
        # This is already enforced by Constraint 2, but we'll keep it for clarity
        total_meals_expr = [x[i, j] for i in range(self.num_meals) for j in range(self.total_meal_slots)]
        problem += lpSum(total_meals_expr) == 7
        
        # Constraint 5: Non-negativity (already handled by IntVar bounds)
        
        logger.info("Added all constraints, solving...")
        
        # Solve
        problem.solve()
        status = LpStatus[problem.status]
        
        if status == "Optimal":
            logger.info("Optimal solution found!")
            
            # Extract solution
            solution = self._extract_solution(x, profile_name)
            solution["status"] = "OPTIMAL"
            solution["objective_value"] = value(problem.objective)
            
            return solution
            
        elif status == "Not Solved":
            # Try with a different solver or check if it's actually feasible
            logger.warning("Solution status: Not Solved, trying alternative approach")
            # PuLP might need a different solver - try default
            problem.solve()
            status = LpStatus[problem.status]
            
            if status == "Optimal":
                solution = self._extract_solution(x, profile_name)
                solution["status"] = "FEASIBLE"
                solution["objective_value"] = value(problem.objective)
                return solution
        
        logger.error(f"No solution found. Status: {status}")
        return {
            "status": "INFEASIBLE",
            "message": f"No feasible solution found. Status: {status}. Try relaxing constraints.",
            "objective_value": None
        }
    
    def _extract_solution(self, x: Dict, profile_name: str) -> Dict:
        """
        Extract solution from solver variables.
        
        Args:
            x: Decision variables dictionary
            profile_name: Profile used for solving
            
        Returns:
            Solution dictionary
        """
        selected_meals = []
        meal_schedule = {}
        
        # Initialize meal schedule
        for day in self.days_of_week:
            meal_schedule[day] = []
        
        # Extract selected meals
        for i in range(self.num_meals):
            for j in range(self.total_meal_slots):
                if x[i, j].varValue is not None and x[i, j].varValue > 0.5:  # Binary variable
                    day_idx = j // self.meals_per_day
                    meal_idx = j % self.meals_per_day
                    day = self.days_of_week[day_idx]
                    
                    meal_info = {
                        "meal": self.meals[i],
                        "day": day,
                        "meal_slot": meal_idx + 1,
                        "cost": self.meals[i]["estimated_cost_usd"]
                    }
                    
                    selected_meals.append(meal_info)
                    meal_schedule[day].append(meal_info)
        
        # Calculate nutritional summary
        nutritional_summary = self._calculate_nutritional_summary(selected_meals)
        
        return {
            "profile_used": profile_name,
            "selected_meals": selected_meals,
            "meal_schedule": meal_schedule,
            "nutritional_summary": nutritional_summary,
            "total_cost": sum(meal["cost"] for meal in selected_meals),
            "num_meals_selected": len(selected_meals)
        }
    
    def _calculate_nutritional_summary(self, selected_meals: List[Dict]) -> Dict:
        """
        Calculate nutritional summary for selected meals.
        
        Args:
            selected_meals: List of selected meal dictionaries
            
        Returns:
            Nutritional summary dictionary
        """
        if not selected_meals:
            return {}
        
        summary = {}
        num_meals = len(selected_meals)
        
        for nutrient in ["calories"] + self.all_nutrients:
            total = sum(self._get_nutrient_value(meal["meal"], nutrient) 
                       for meal in selected_meals)
            average = total / num_meals
            summary[nutrient] = {
                "total": total,
                "average": average
            }
        
        return summary
    
    def print_solution(self, solution: Dict):
        """
        Print a formatted solution.
        
        Args:
            solution: Solution dictionary from solve()
        """
        if solution["status"] not in ["OPTIMAL", "FEASIBLE"]:
            print(f"Status: {solution['status']}")
            print(f"Message: {solution.get('message', 'No message')}")
            return
        
        print("=" * 60)
        print("MEAL PLANNING OPTIMIZATION RESULTS")
        print("=" * 60)
        print(f"Profile: {solution['profile_used']}")
        print(f"Status: {solution['status']}")
        print(f"Total Cost: ${solution['total_cost']:.2f}")
        print(f"Number of Meals: {solution['num_meals_selected']}")
        print()
        
        print("WEEKLY MEAL SCHEDULE:")
        print("-" * 40)
        for day in self.days_of_week:
            meals = solution['meal_schedule'][day]
            if meals:
                print(f"{day}:")
                for meal in meals:
                    print(f"  Meal {meal['meal_slot']}: {meal['meal']['title']} (${meal['cost']:.2f})")
            else:
                print(f"{day}: No meals scheduled")
            print()
        
        print("NUTRITIONAL SUMMARY:")
        print("-" * 40)
        for nutrient, values in solution['nutritional_summary'].items():
            print(f"{nutrient.replace('_', ' ').title()}: "
                  f"Total={values['total']:.1f}, Average={values['average']:.1f}")
        print()


def main():
    """Example usage of the MealOptimizer."""
    try:
        # Initialize optimizer
        optimizer = MealOptimizer()
        
        # Solve for different profiles
        profiles_to_try = ["healthy-adult", "weight-loss", "keto"]
        
        for profile in profiles_to_try:
            print(f"\n{'='*80}")
            print(f"SOLVING FOR PROFILE: {profile.upper()}")
            print(f"{'='*80}")
            
            solution = optimizer.solve(profile_name=profile, max_meals_per_meal=2)
            optimizer.print_solution(solution)
            
            if solution["status"] not in ["OPTIMAL", "FEASIBLE"]:
                print(f"Could not find solution for {profile} profile")
                continue
    
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    main()
