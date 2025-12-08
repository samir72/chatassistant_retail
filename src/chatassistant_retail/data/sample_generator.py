"""Sample data generator for retail inventory and sales."""

import random
import uuid
from datetime import datetime, timedelta

from faker import Faker

from .models import Product, Sale


class SampleDataGenerator:
    """Generate realistic sample data for retail inventory system."""

    CATEGORIES = [
        "Electronics",
        "Clothing",
        "Groceries",
        "Home & Garden",
        "Sports & Outdoors",
        "Books & Media",
        "Toys & Games",
        "Health & Beauty",
    ]

    PRODUCT_TEMPLATES = {
        "Electronics": [
            "Wireless Mouse",
            "Keyboard",
            "Monitor",
            "Laptop",
            "Headphones",
            "Smartphone",
            "Tablet",
            "USB Cable",
            "Power Bank",
            "Webcam",
        ],
        "Clothing": [
            "T-Shirt",
            "Jeans",
            "Jacket",
            "Sneakers",
            "Dress",
            "Sweater",
            "Hoodie",
            "Shorts",
            "Socks",
            "Cap",
        ],
        "Groceries": [
            "Organic Apples",
            "Whole Wheat Bread",
            "Fresh Milk",
            "Orange Juice",
            "Coffee Beans",
            "Pasta",
            "Rice",
            "Olive Oil",
            "Cereal",
            "Eggs",
        ],
        "Home & Garden": [
            "LED Light Bulb",
            "Plant Pot",
            "Garden Hose",
            "Lawn Mower",
            "Tool Set",
            "Paint Brush",
            "Storage Box",
            "Door Mat",
            "Picture Frame",
            "Curtains",
        ],
        "Sports & Outdoors": [
            "Yoga Mat",
            "Dumbbell Set",
            "Tennis Racket",
            "Basketball",
            "Camping Tent",
            "Hiking Boots",
            "Water Bottle",
            "Bicycle",
            "Running Shoes",
            "Fitness Tracker",
        ],
        "Books & Media": [
            "Fiction Novel",
            "Cookbook",
            "Blu-ray Movie",
            "Board Game",
            "Puzzle",
            "Art Supplies",
            "Music CD",
            "Magazine",
            "Journal",
            "Coloring Book",
        ],
        "Toys & Games": [
            "Action Figure",
            "Building Blocks",
            "Doll",
            "Remote Control Car",
            "Puzzle",
            "Board Game",
            "Stuffed Animal",
            "Play-Doh Set",
            "Toy Train",
            "Card Game",
        ],
        "Health & Beauty": [
            "Shampoo",
            "Face Cream",
            "Toothpaste",
            "Hand Sanitizer",
            "Makeup Kit",
            "Hair Dryer",
            "Vitamins",
            "Body Lotion",
            "Deodorant",
            "Nail Polish",
        ],
    }

    def __init__(self, seed: int = 42):
        """
        Initialize the sample data generator.

        Args:
            seed: Random seed for reproducibility
        """
        self.fake = Faker()
        Faker.seed(seed)
        random.seed(seed)

    def generate_products(self, count: int = 500) -> list[Product]:
        """
        Generate sample products across categories.

        Args:
            count: Number of products to generate

        Returns:
            List of Product instances
        """
        products = []

        for i in range(count):
            category = random.choice(self.CATEGORIES)
            product_template = random.choice(self.PRODUCT_TEMPLATES[category])

            # Add variation to product names
            variations = ["Pro", "Plus", "Premium", "Deluxe", "Standard", "Basic"]
            colors = ["Red", "Blue", "Green", "Black", "White", "Silver"]

            if random.random() > 0.5:
                name = f"{random.choice(variations)} {product_template}"
            else:
                name = f"{product_template} ({random.choice(colors)})"

            # Generate stock levels with realistic distribution
            stock_distribution = random.random()
            if stock_distribution < 0.60:  # 60% normal stock
                current_stock = random.randint(30, 200)
            elif stock_distribution < 0.85:  # 25% low stock
                current_stock = random.randint(1, 20)
            elif stock_distribution < 0.95:  # 10% out of stock
                current_stock = 0
            else:  # 5% overstocked
                current_stock = random.randint(201, 500)

            reorder_level = random.randint(10, 50)

            product = Product(
                sku=f"SKU-{10000 + i:05d}",
                name=name,
                category=category,
                price=round(self._generate_category_price(category), 2),
                current_stock=current_stock,
                reorder_level=reorder_level,
                supplier=self.fake.company(),
                description=self.fake.text(max_nb_chars=200),
                image_url=f"https://placeholder.co/400x400?text={product_template.replace(' ', '+')}",
            )
            products.append(product)

        return products

    def _generate_category_price(self, category: str) -> float:
        """Generate realistic price based on category."""
        price_ranges = {
            "Electronics": (19.99, 999.99),
            "Clothing": (9.99, 199.99),
            "Groceries": (1.99, 49.99),
            "Home & Garden": (4.99, 299.99),
            "Sports & Outdoors": (14.99, 599.99),
            "Books & Media": (5.99, 79.99),
            "Toys & Games": (7.99, 149.99),
            "Health & Beauty": (3.99, 99.99),
        }

        min_price, max_price = price_ranges.get(category, (5.99, 99.99))
        return random.uniform(min_price, max_price)

    def generate_sales_history(self, products: list[Product], months: int = 6) -> list[Sale]:
        """
        Generate sales history with seasonal patterns.

        Args:
            products: List of products to generate sales for
            months: Number of months of history to generate

        Returns:
            List of Sale instances
        """
        sales = []
        start_date = datetime.now() - timedelta(days=30 * months)

        for day_offset in range(30 * months):
            current_date = start_date + timedelta(days=day_offset)

            # Get seasonal multiplier
            seasonal_multiplier = self._get_seasonal_multiplier(current_date)

            # Base daily sales count varies by day of week
            if current_date.weekday() < 5:  # Weekday
                base_sales_count = random.randint(50, 100)
            else:  # Weekend
                base_sales_count = random.randint(80, 150)

            daily_sales_count = int(base_sales_count * seasonal_multiplier)

            for _ in range(daily_sales_count):
                # Select product with weighted probability (popular items sell more)
                product = self._select_product_weighted(products)

                # Generate sale time during business hours (9am - 9pm)
                hour = random.randint(9, 20)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                timestamp = current_date.replace(hour=hour, minute=minute, second=second)

                # Price variation: -10% to +10%
                price_variation = random.uniform(0.9, 1.1)
                sale_price = round(product.price * price_variation, 2)

                # Quantity: most sales are 1-2 items, occasionally bulk
                quantity_rand = random.random()
                if quantity_rand < 0.7:  # 70% single item
                    quantity = 1
                elif quantity_rand < 0.9:  # 20% two items
                    quantity = 2
                elif quantity_rand < 0.97:  # 7% small bulk (3-5)
                    quantity = random.randint(3, 5)
                else:  # 3% large bulk (6-20)
                    quantity = random.randint(6, 20)

                # Channel distribution
                channel_rand = random.random()
                if channel_rand < 0.5:  # 50% retail
                    channel = "retail"
                elif channel_rand < 0.85:  # 35% online
                    channel = "online"
                else:  # 15% wholesale
                    channel = "wholesale"

                sale = Sale(
                    sale_id=str(uuid.uuid4()),
                    sku=product.sku,
                    quantity=quantity,
                    sale_price=sale_price,
                    timestamp=timestamp,
                    channel=channel,
                )
                sales.append(sale)

        return sales

    def _get_seasonal_multiplier(self, date: datetime) -> float:
        """
        Get seasonal sales multiplier.

        Higher sales in Q4 (holiday season), lower in Q1.
        """
        month = date.month

        if month in [11, 12]:  # Nov-Dec: Holiday season
            return random.uniform(1.3, 1.6)
        elif month in [1, 2]:  # Jan-Feb: Post-holiday slump
            return random.uniform(0.7, 0.9)
        elif month in [7, 8]:  # Jul-Aug: Summer sales
            return random.uniform(1.1, 1.3)
        else:  # Other months: Normal
            return random.uniform(0.95, 1.05)

    def _select_product_weighted(self, products: list[Product]) -> Product:
        """
        Select a product with weighted probability.

        Products with higher stock levels and lower prices are more likely to be sold.
        """
        # Create weights based on stock and price
        weights = []
        for product in products:
            # Higher stock = higher chance of being sold
            stock_weight = min(product.current_stock, 100) / 100.0

            # Lower price = higher chance of being sold
            price_weight = 1.0 / (1.0 + product.price / 100.0)

            # Combined weight
            weight = (stock_weight * 0.6 + price_weight * 0.4) + 0.1  # Ensure min weight

            weights.append(weight)

        return random.choices(products, weights=weights, k=1)[0]
