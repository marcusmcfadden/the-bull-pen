# The Bull Pen: Accountability Tracker
As a third-year cadet at Duke and NCCU's Army ROTC: "The Bull City Battlion," I am no stranger to the lack of optimization present in both cadet personal information as well as accountability on important days and events for the organization. The Bull Pen: Accountability Tracker aims to not only optimize accountability, but to include added functionality; profiles, protected database entries, and improved UI functionality. 

## How It's Made:

**Tech used:** Python, Flet (Flutter/Material Design), SQLite

Developing this application required a deep dive into the Flet framework, which allowed me to leverage the speed of Python with the polished, responsive UI of Flutter’s Material Design.

    Logic over Syntax: I focused heavily on creating a modular backend. Instead of hard-coding cadet data, I built a relational database using SQLite. This ensures that even if the app closes or the system crashes, no "boots on the ground" data is lost.

    The User-Centric UI: Understanding that cadets might be using this at 0530 during a rainy APFT, I prioritized high-contrast Material Design elements and large touch targets. I didn't just want it to work; I wanted it to be "Soldier-proof."

    State Management: I implemented custom logic to handle real-time UI updates. When a cadet’s status changes in the database, the Flet UI reflects that change instantly without requiring a full page refresh, mimicking the responsiveness of high-end enterprise software.

## Optimizations

Database Normalization: Originally, I was storing all data in a single, massive table. I refactored the schema to use relational keys, which significantly reduced data redundancy and made queries for specific squads or platoons much faster.

Asynchronous Processing: To keep the UI from "freezing" during heavy database writes, I utilized Python’s asynchronous capabilities. This ensures that the user can keep navigating the app while the database handles the heavy lifting in the background.

Asset Management: I optimized the way the app handles icons and images, ensuring the executable remains lightweight enough to be shared easily among unit leadership without requiring a complex installation process.

## Lessons Learned:

The Intersection of Lead & Tech: The biggest takeaway wasn't a line of code, but the realization that technical competence is a leadership multiplier. Being able to identify a friction point in the battalion and build a solution from scratch gave me a new perspective on "Leading from the Front."

Security Mindset: Building the "Protected Database Entries" taught me the importance of data validation. I learned that you have to assume the user will input the wrong data type and build "guardrails" to prevent the database from breaking—a core tenet of the Cyber branch mindset.

Iterative Design: I learned that "done is better than perfect." I spent hours over-engineering a single feature, only to realize that the end-user (my fellow cadets) just needed a simple, working button. It taught me to prioritize mission-essential functions over "flashy" extras.


