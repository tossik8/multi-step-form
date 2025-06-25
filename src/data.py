def get_plans():
    return [
        {
            "id": 1,
            "name": "Arcade",
            "img": "images/icon-arcade.svg",
            "price": {
                "yearly": 90,
                "monthly": 9
            }
        },
        {
            "id": 2,
            "name": "Advanced",
            "img": "images/icon-advanced.svg",
            "price": {
                "yearly": 120,
                "monthly": 12
            }
        },
        {
            "id": 3,
            "name": "Pro",
            "img": "images/icon-pro.svg",
            "price": {
                "yearly": 150,
                "monthly": 15
            }
        }
    ]


def get_add_ons():
    return [
    {
        "id": 1,
        "title": "Online service",
        "description": "Access to multiplayer games",
        "price": {
            "yearly": 10,
            "monthly": 1
        }
    },
    {
        "id": 2,
        "title": "Larger storage",
        "description": "Extra 1TB of cloud save",
        "price": {
            "yearly": 20,
            "monthly": 2
        }
    },
    {
        "id": 3,
        "title": "Customizable profile",
        "description": "Custom theme on your profile",
        "price": {
            "yearly": 20,
            "monthly": 2
        }
    }
]