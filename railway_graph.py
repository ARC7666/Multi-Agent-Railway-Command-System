import networkx as nx

def create_railway_network() -> nx.Graph:
    """
    Creates and returns a NetworkX graph representing the core Eastern Railway stations
    and their multi-track connections.

    Returns:
        nx.Graph: The railway network graph.
    """
    G = nx.Graph()
    
    # Core Eastern Railway Stations (Simplified to major sections)
    stations: dict[str, dict[str, float]] = {
        "Howrah (HWH)": {"lat": 22.5839, "lon": 88.2500},
        "Sealdah (SDAH)": {"lat": 22.5200, "lon": 88.4500},
        "Bandel (BDC)": {"lat": 22.9234, "lon": 88.3769},
        "Bardhaman (BWN)": {"lat": 23.2393, "lon": 87.8615},
        "Durgapur (DGR)": {"lat": 23.4975, "lon": 87.3155},
        "Asansol (ASN)": {"lat": 23.6871, "lon": 86.9746}
    }
    
    for name, coords in stations.items():
        G.add_node(name, lat=coords["lat"], lon=coords["lon"])
        
    # Multi-Track Sections
    # Direction: UP is towards Asansol, DN is towards Howrah/Sealdah
    G.add_edge("Howrah (HWH)", "Bandel (BDC)", tracks={"UP1": "active", "UP2": "active", "DN1": "active", "DN2": "active"})
    G.add_edge("Sealdah (SDAH)", "Bandel (BDC)", tracks={"UP1": "active", "DN1": "active"}) # Branch line
    G.add_edge("Bandel (BDC)", "Bardhaman (BWN)", tracks={"UP1": "active", "UP2": "active", "DN1": "active", "DN2": "active"})
    G.add_edge("Bardhaman (BWN)", "Durgapur (DGR)", tracks={"UP1": "active", "UP2": "active", "DN1": "active", "DN2": "active"})
    G.add_edge("Durgapur (DGR)", "Asansol (ASN)", tracks={"UP1": "active", "UP2": "active", "DN1": "active", "DN2": "active"})
    
    return G
