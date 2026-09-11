# Madrid EV points map

## Intro

An interactive dashboard with information related to the distribution of public-use EV charging points around the city of Madrid. Directed to EV users, or any curious person that wants to analyze the EVs' presence in this city.


## Preview

### [Insert GIF of website to show off its features]


## The problem to be solved

Finding a public EV charging point for your vehicle can be a hassle in a city like Madrid, specially if you
don't know where to look. And even though there already exist datasets and websites with this information, some can be lacking in paramount data. 
 
Madrid's city council publishes an open dataset of public EV charging spots, but its data is static and sometimes incomplete: it can't inform about the current operational status nor costs per kW. Meanwhile, APIs like OpenChargeMap are able to provide worldwide real-time data, but it also overgeneralizes certain atributes like neighborhoods or types of management over these stations, while a local institution database can provide.

This project merges these two sources (matching each point from the local dataset with its geographically closest from the API) to answer three questions:
 
- Where are the nearest charging points to me, and what types of connectors are available?
- What neighborhoods in Madrid are least served?
- What operators dominate the market and what do they offer?


## Demo

### [Insert link to the project deployed on Streamlit Cloud]


## Features

- An interactive map with popups of all EV stations represented, and filled with details like the type of connectors they have, costs, address, etc. The map is also equipped with clustering and a simple location search engine.
- Combinable filters to filter out EV stations based on: neighborhood, type of management, operator company and type of connectors they offer.
- Option to export the filtered results to a CSV file.
- Board with relevant statistics about the data.


## Architecture

### [Diagram of the entire structure and architecture of the project, including file names]


## Technical decisions taken

1. Passing coordinates from Madrid's datatset from UTM format to WGS84.

Folium's mapping function (folium.Map), which was chosen because Streamlit's native maps (streamlit.map) don't support custom popups; manages exclusively WGS84 coordinates, which are standard latitude and longitude decimal degrees [latitude, longitude]. 

2. Retry with Tenacity library for failed HTTP requests to OpenChargeMap API.

If OpenChargeMap fails o hits rate-limit, the app would probably break. Thus, its necessary to add a retry strategy and explicit timeouts in requests.get to make sure there is a contigency plan in case the API fails.

Tenacity is the most popular general-purpose retry library in the Python ecosystem (it's a fork of the now-archived 'retrying' library). It works as a decorator and is much more flexible than the 'urllib3' Retry adapter — you can retry based on exceptions, response content, custom predicates, or all three together.

- https://scrapeops.io/python-web-scraping-playbook/python-requests-retry-failed-requests/#retry-failed-requests-using-tenacity
- https://tenacity.readthedocs.io/en/latest/ 

3. Matching of EV-points by geographic distance.

Given the absence of an individual ID atribute for these EV stations in Madrid's dataset and considering that, in case such an atribute existed, these two data sources would not share a common ID assigning method; these points can only be matched in terms of physical closeness. 

Having into account the dataset and the API won't have the exact same coordinates for each charging point, we can only achieve closest matches relative to geographical distance.

4. Use a BallTree to find an OCM match for the CSV file's EV points.

The classic way of matching the EV points from both data sources would be, once the API request has been answered successfully, to iterate through every station from the local dataset and then, for each EV station, iterate through all points from the API to get its closest match.

However, this method would have a time complexity of (N x M) (being N the size of the local dataset and M the size of the API response). A better way to optimize the matching process is to organize the station points from the OCM API into a 'BallTree'.

BallTrees are hierarchical binary-tree-based data structures designed for organizing and querying points in multidimensional spaces (like [latitude, longitude] coordinates). As a binary tree, each non-leaf node represents a hypersphere containing a subset of the data, and each leaf node corresponds to a small subset of points. Thus, unlike KD-trees, Ball trees use hyperspheres to represent partitions, grouping nearby points within each hypersphere based on geographic proximity. 

BallTree's design facilitates fast nearest neighbor searches, as it allows for the rapid elimination of entire subtrees during the search process. This, combined with its compatibility with the use of non-Euclidean distances like the 'Harvesian distance' (distance between two points in a straight line over a sphere; perfect for resembling distances over Earth's surface) makes BallTrees the perfect solution to optimize these matches between Madrid's dataset and OCM API. As a result, the time complexity lowers to (N x log(M))

- https://www.geeksforgeeks.org/machine-learning/ball-tree-and-kd-tree-algorithms/ 
- https://medium.com/@geethasreemattaparthi/ball-tree-and-kd-tree-algorithms-a03cdc9f0af9 
- https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.haversine_distances.html 

5. Using Parquet as a valid format for cache processed data.

Even though Pandas library offers many options to write and save our data (i.e. to_csv, to_parquet, to_excel, etc.), like the cache processed data of this project; 'Parquet' format was chosen because of its columnar style format that makes it faster to read and analyze data; while its advanced compression algorithms save greatly on data storage compared to more traditional formats like CSV or Excel.

- https://medium.com/@aiiaor/which-data-file-format-to-use-csv-json-parquet-avro-orc-e7a9acaaa7df 


## Tech Stack

`Python` · `Streamlit` · `Folium` · `Plotly` · `Pandas` · `Numpy` · `Tenacity`


## How to execute it locally?
 
```bash
    git clone https://github.com/sofiac1024/ev-charging-madrid.git
    cd ev-charging-madrid
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    
    cp .env.example .env
    # Edit .env and add your API_KEY from OpenChargeMap (you can get it free in openchargemap.org)
    
    streamlit run app.py
```
