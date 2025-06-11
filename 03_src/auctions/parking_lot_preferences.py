import numpy as np

def min_price(buyer_id, auction_ids, bids):
    """Computes preferences based only on current bids."""
    return np.argmin(bids)

class MinDistancePreference:
    """Computes preferences based on distance to a particular parking lot.
       It results in prefering the closest parking alternative against more distant ones."""
    def __init__(self, distance_mtx, parking_capacities):
        self.distance_mtx = distance_mtx
            
        self.parking_ranges = []
        last = 0
        for caps in parking_capacities:
            for i in range(caps):
                self.parking_ranges.append(last+caps)
            last = last+caps
            
            
    def __call__(self, buyer_id, auction_ids, bids):
        active_indices = [auc_id.split("_")[1] for auc_id in auction_ids]
        distance_vector = []
        for act in active_indices:
            distance_vector.append(self.distance_mtx[buyer_id][act])
        
        return np.argmin(distance_vector)
        
        
class BalancedCostDistancePreference(MinDistancePreference):
    """Computes preferences based on 0.5*cost+0.5*distance function.
       That results in prefering closer and cheaper parking against the more expensive and more distant ones.
       (Values gets normalized during calculation.)"""
    def __call__(self, buyer_id, auction_ids, bids):
        max_dist = max(list(self.distance_mtx[buyer_id].values()))
        max_bid = max(list(bids.values()))
        best_val = 10000
        best_auc_id = None
        
        for ac in bids:
            edge = ac.split("_")[1]
            pref_fn = bids[ac]/max_bid + self.distance_mtx[buyer_id][edge]/max_dist
            if pref_fn < best_val:
                best_val = pref_fn
                best_auc_id = ac
            
        return best_auc_id
    
class WeighedCostDistancePreference(MinDistancePreference):
    """Computes preferences based on beta*cost+(1-beta)*distance function.
       That results in prefering closer and cheaper parking against the more expensive and more distant ones.
       (Values gets normalized during calculation.)"""
    def __call__(self, buyer_id, auction_ids, bids):
        max_dist = max(list(self.distance_mtx[buyer_id].values()))
        max_bid = max(list(bids.values()))
        best_val = 10000
        best_auc_id = None
        
        for ac in bids:
            edge = ac.split("_")[1]
            pref_fn = bids[ac]/max_bid + self.distance_mtx[buyer_id][edge]/max_dist
            if pref_fn < best_val:
                best_val = pref_fn
                best_auc_id = ac
            
        return best_auc_id
