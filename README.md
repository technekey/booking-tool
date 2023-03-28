# booking-tool
This is a straightforward basic tool built on top of the Flask backend. This can be used to book Rooms, Servers, K8s-clusters, shifts, etc., between a pool of people. This application is configurable using the config.json file provided in the repo. 

    
`RESOURCE_INFO`: Here specify the Resource name and a unique color against it.     
`DB_FILE`: This file will hold all the booking records. This is a temp solution, will be migrated to a DB.    
`USER_DB`: This will hold user credentials. This is a temp solution, will be migrated to a DB.    
`LOG_FILE`: A file path to store all the logs of run time.    
`ADMIN_INFO`: This file contains the admin credentials.    
`HOST`: The Host IP to listen    
`PORT`: The port to listen on.    
`TZ`: Time zone    
`REGISTRATION_ALLOWED`: Allow self registration by public. (Admin may always register a user regardless of this value)    
`ALLOWED_DOMAINS`: The users with these domains are allowed to register.    
`TITLE`: Title message to show on each page.    
`FOOTER_MESSAGE`: Message to show on footer of each page.       
`RESOURCE_NAME`: This could be set to the type of resource, like a "meeting room", "Cluster", "shift" etc.    


```
{
    "RESOURCE_INFO": {
        "Cluster-1": "blue",
        "Cluster-2": "green",
        "Cluster-3": "red",
        "Cluster-4": "gray",
        "Cluster-5": "yellow"
    },
    "DB_FILE": "./bookings.db.json",
    "USER_DB": "./users_info.db.json",
    "LOG_FILE": "login.logs",
    "ADMIN_INFO": "admins.db.json",
    "HOST": "0.0.0.0",
    "PORT": "8080",
    "TZ": "CST",
    "REGISTRATION_ALLOWED": true,
    "ALLOWED_DOMAINS": ["bar.com","zoo.com"],
    "TITLE": "Resource Reservation Page",
    "FOOTER_MESSAGE": "For User registration, please email at admin@foobar.com",
    "RESOURCE_NAME": "Kubernetes Cluster"

}
```

**Installation and execution:**

Please see the `requirements.txt` file for dependencies.  The initial admin credentials are located in `admins.db.json` file. 

**NOTE**: 

1. This tool is a test tool, not intended for any serious use unless you evaluvate and modify for yourself and find it fit. 
2. A big disadvantage is it depends on File read/write for any operation instead of DB. Althogh the files are secured with `600` permissions as soon as they are created. 
3. This application was originally designed as a test application. So may not be best suited for any real usecase. 

The front-end uses the following JS libraries:

+ jquery-3.6.0.min.js
+ jquery.datetimepicker.full.min.js
+ moment.min.js
+ fullcalendar.min.js


**PS:** Feel free to improve this application for better security and DB usage if you have time and resoures.
