db = db.getSiblingDB('app');

db.createCollection('sessions', {})
db.createCollection('recipes', {})

db.recipes.insertMany([
    {
        'title': 'Orange Juice',
        text: 'grab an orange, slice the orange, squeeze in a wine glass, enjoy',
        'steps': [
            {'text': 'grab an orange', 'noun': 'orange', 'estimatedTime': 5},
            {'text': 'slice the orange', 'noun': 'knife', 'estimatedTime': 5},
            {'text': 'squeeze in a wine glass', 'noun': 'wine glass', 'estimatedTime': 5},
            {'text': 'enjoy', 'noun':'person', 'estimatedTime': 5},
        ],
    },
])