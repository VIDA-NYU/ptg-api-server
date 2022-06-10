db = db.getSiblingDB('app');

db.createCollection('sessions', {})
db.createCollection('recipes', {})
db.createCollection('recipes', {})


db.recipes.insertMany([
//     {
//         'title': 'Orange Juice',
//         text: 'grab an orange, slice the orange, squeeze in a wine glass, enjoy',
//         'steps': [
//             {'text': 'grab an orange', 'noun': 'orange', 'estimatedTime': 5},
//             {'text': 'slice the orange', 'noun': 'knife', 'estimatedTime': 5},
//             {'text': 'squeeze in a wine glass', 'noun': 'wine glass', 'estimatedTime': 5},
//             {'text': 'enjoy', 'noun':'person', 'estimatedTime': 5},
//         ],
//     },

{
  "name":"Pinwheels",
  "ingredients":[
    "1 8-inch flour tortilla",
    "Jar of nut butter or allergy-friendly alternative (such as sunbutter, soy butter, or seed butter)",
    "Jar of jelly, jam, or fruit preserves"
  ],
  "tools":[
    "cutting board",
    "butter knife",
    "paper towel",
    "toothpicks",
    "~12-inch strand of dental floss",
    "plate"
  ],
  "instructions":[
    "Place tortilla on cutting board.",
    "Use a butter knife to scoop about a tablespoon of nut butter from the jar. Spread nut butter onto tortilla, leaving 1/2-inch uncovered at the edges.",
    "Clean the knife by wiping with a paper towel.",
    "Use the knife to scoop about a tablespoon of jelly from the jar. Spread jelly over the nut butter.",
    "Clean the knife by wiping with a paper towel.",
    "Roll the tortilla from one end to the other into a log shape, about 1.5 inches thick. Roll it tight enough to prevent gaps, but not so tight that the filling leaks.",
    "Secure the rolled tortilla by inserting 5 toothpicks about 1 inch apart.",
    "Trim the ends of the tortilla roll with the butter knife, leaving 1⁄2 inch margin between the last toothpick and the end of the roll. Discard ends.",
    "Slide floss under the tortilla, perpendicular to the length of the roll. Place the floss halfway between two toothpicks.",
    "Cross the two ends of the floss over the top of the tortilla roll. Holding one end of the floss in each hand, pull the floss ends in opposite directions to slice.",
    "Continue slicing with floss to create 5 pinwheels.",
    "Place the pinwheels on a plate."
  ]
},



{
  "name":"Pour-over Coffee",
  "ingredients":[
    "12 oz water",
    "25 grams whole coffee beans"
  ],
  "tools":[
    "2-cup liquid measuring cup",
    "electric kettle",
    "kitchen scale",
    "coffee grinder",
    "filter cone dripper (stainless steel)",
    "paper basket filter (standard 8-12 cup size)",
    "12-ounce coffee mug",
    "thermometer",
    "timer (optional)"
  ],
  "instructions":[
    "Measure 12 ounces of cold water and transfer to a kettle.",
    "While the water is boiling, assemble the filter cone. Place the dripper on top of a coffee mug.",
    "Prepare the filter insert by folding the paper filter in half to create a semi-circle, and in half again to create a quarter-circle. Place the paper filter in the dripper and spread open to create a cone.",
    "Weigh the coffee beans and grind until the coffee grounds are the consistency of course sand, about 20 seconds. Transfer the grounds to the filter cone.",
    "Once the water has boiled, check the temperature. The water should be between 195-205 degrees Fahrenheit or between 91-96 degrees Celsius. If the water is too hot, let it cool briefly.",
    "Pour a small amount of water in the filter to wet the grounds. Wait for coffee to bloom, about 30 seconds. You will see small bubbles or foam on the coffee grounds during this step.",
    "Slowly pour the rest of the water over the grounds in a circular motion. Do not overfill beyond the top of the paper filter.",
    "Let the coffee drain completely into the mug before removing the dripper. Discard the paper filter and coffee grounds."
  ]
},



{
  "name":"Mug Cake",
  "ingredients":[
    "2 Tablespoons all-purpose flour",
    "1.5 Tablespoons granulated sugar",
    "1⁄4 teaspoon baking powder",
    "Pinch salt",
    "2 teaspoons canola or vegetable oil",
    "2 Tablespoons water",
    "1⁄4 teaspoon vanilla extract",
    "Container of chocolate frosting (premade)"
  ],
  "tools":[
    "measuring spoons",
    "small mixing bowl",
    "whisk",
    "paper cupcake liner",
    "12-ounce coffee mug",
    "plate",
    "microwave",
    "zip-top bag, snack or sandwich size",
    "scissors",
    "spoon"
  ],
  "instructions":[
    "Place the paper cupcake liner inside the mug. Set aside.",
    "Measure and add the flour, sugar, baking powder, and salt to the mixing bowl.",
    "Whisk to combine.",
    "Measure and add the oil, water, and vanilla to the bowl.",
    "Whisk batter until no lumps remain.",
    "Pour batter into prepared mug.",
    "Microwave the mug and batter on high power for 60 seconds.",
    "Check the cake for doneness; it should be mostly dry and springy at the top. If the cake still looks wet, microwave for an additional 5 seconds.",
    "Invert the mug to release the cake onto a place. Carefully remove paper liner.",
    "While the cake is cooling, prepare to pipe the frosting. Scoop a spoonful of chocolate frosting into a zip-top bag and seal, removing as much air as possible.",
    "Use scissors to cut one corner from the bag to create a small opening 1⁄4-inch in diameter.",
    "Squeeze the frosting through the opening to apply small dollops of frosting to the plate in a circle around the base of the cake."
  ]
},



])
