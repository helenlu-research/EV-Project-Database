"""
Staggered Evacuation Distribution Module

This module provides functionality to generate staggered evacuation distributions
following various probability distributions (currently Beta). All R_ilt values
represent integers (number of EVs) and are guaranteed to sum to E_il over time.

Author: Helen Lu
Date: 2026-05-12
"""

import numpy as np
from scipy import stats


class StaggeredEvacuationDistributions:
    """
    Generate staggered evacuation distributions for EV evacuations.
    
    All R_ilt values are integers representing the number of EVs entering 
    the network at time t from location i with charge level l.
    
    Constraint: sum_{t} R_ilt = E_il for all i, l
    """
    
    @staticmethod
    def beta_distribution(E_il, T, alpha, beta, random_state=None):
        """
        Generate staggered evacuation distribution using Beta distribution.
        
        Parameters
        ----------
        E_il : array-like
            Total number of EVs to evacuate from location i with charge level l.
            Shape: (num_locations, num_charge_levels) or scalar
        T : int
            Number of time periods
        alpha : float
            Shape parameter α for Beta distribution (α > 0)
        beta : float
            Shape parameter β for Beta distribution (β > 0)
        random_state : int, optional
            Random seed for reproducibility
            
        Returns
        -------
        R_ilt : np.ndarray
            Integer staggered evacuation distribution.
            Shape: same as E_il, with additional dimension T at the end.
            Example: if E_il shape is (I, L), then R_ilt shape is (I, L, T)
        """
        if random_state is not None:
            np.random.seed(random_state)
        
        # Convert E_il to numpy array
        E_il = np.asarray(E_il, dtype=int)
        original_shape = E_il.shape
        E_il_flat = E_il.flatten()
        
        # Initialize output array
        R_ilt = np.zeros((E_il_flat.shape[0], T), dtype=int)
        
        # Generate Beta samples for each location-charge level
        for idx, e_il in enumerate(E_il_flat):
            if e_il == 0:
                # No evacuations needed
                continue
            
            # Generate normalized Beta samples
            beta_samples = np.random.beta(alpha, beta, size=T)
            normalized_samples = beta_samples / np.sum(beta_samples)
            
            # Distribute E_il EVs across time periods
            continuous_distribution = e_il * normalized_samples
            
            # Convert to integers ensuring sum equals E_il
            R_ilt[idx, :] = StaggeredEvacuationDistributions._continuous_to_integer(
                continuous_distribution, e_il
            )
        
        # Reshape back to original dimensions + time dimension
        output_shape = original_shape + (T,)
        R_ilt = R_ilt.reshape(output_shape)
        
        return R_ilt
    
    @staticmethod
    def _continuous_to_integer(continuous_dist, total_count):
        """
        Convert continuous distribution to integers while preserving sum.
        
        Uses largest remainder method to ensure:
        1. All values are non-negative integers
        2. Sum equals total_count exactly
        
        Parameters
        ----------
        continuous_dist : np.ndarray
            Continuous distribution values
        total_count : int
            Target sum for the integer distribution
            
        Returns
        -------
        integer_dist : np.ndarray
            Integer distribution with sum = total_count
        """
        # Start with floor of each value
        integer_dist = np.floor(continuous_dist).astype(int)
        
        # Calculate remainder for each element
        remainder = continuous_dist - integer_dist
        
        # Distribute remaining count to elements with largest remainders
        deficit = total_count - np.sum(integer_dist)
        if deficit > 0:
            # Get indices sorted by remainder (descending)
            indices_sorted = np.argsort(-remainder)
            # Add 1 to the indices with largest remainders
            for i in range(deficit):
                integer_dist[indices_sorted[i]] += 1
        elif deficit < 0:
            # Handle edge case where floor overshoots
            indices_sorted = np.argsort(remainder)
            for i in range(-deficit):
                if integer_dist[indices_sorted[i]] > 0:
                    integer_dist[indices_sorted[i]] -= 1
        
        return integer_dist
    
    @staticmethod
    def generate_beta_scenarios(E_il, T, scenarios, random_state=None):
        """
        Generate multiple Beta distribution scenarios with flexible parameter tuning.
        
        Parameters
        ----------
        E_il : array-like
            Total number of EVs to evacuate from location i with charge level l.
            Shape: (num_locations, num_charge_levels) or scalar
        T : int
            Number of time periods
        scenarios : dict
            Dictionary of scenarios with format:
            {
                "scenario_name": {"alpha": float, "beta": float},
                ...
            }
            Example:
            {
                "early_evac": {"alpha": 2, "beta": 5},
                "delayed_evac": {"alpha": 5, "beta": 2},
                "baseline": {"alpha": 1, "beta": 1}
            }
        random_state : int, optional
            Random seed for reproducibility. Applied to all scenarios.
            
        Returns
        -------
        results : dict
            Dictionary with same keys as scenarios, values are R_ilt arrays.
            Example:
            {
                "early_evac": np.array(...),
                "delayed_evac": np.array(...),
                "baseline": np.array(...)
            }
        """
        results = {}
        
        for scenario_name, params in scenarios.items():
            if "alpha" not in params or "beta" not in params:
                raise ValueError(
                    f"Scenario '{scenario_name}' must have 'alpha' and 'beta' keys"
                )
            
            R_ilt = StaggeredEvacuationDistributions.beta_distribution(
                E_il=E_il,
                T=T,
                alpha=params["alpha"],
                beta=params["beta"],
                random_state=random_state
            )
            
            # Validate
            StaggeredEvacuationDistributions.validate_distribution(
                R_ilt, E_il, scenario_name
            )
            
            results[scenario_name] = R_ilt
        
        return results
    
    @staticmethod
    def validate_distribution(R_ilt, E_il, scenario_name=""):
        """
        Validate that distribution sums correctly.
        
        Parameters
        ----------
        R_ilt : np.ndarray
            Staggered evacuation distribution
        E_il : array-like
            Expected totals
        scenario_name : str, optional
            Name of scenario for error messages
            
        Raises
        ------
        AssertionError
            If distribution doesn't sum correctly or contains non-integers
        """
        E_il = np.asarray(E_il)
        
        # Check that R_ilt are integers
        assert np.all(R_ilt == R_ilt.astype(int)), \
            f"Scenario '{scenario_name}': R_ilt must contain only integers"
        
        # Check that R_ilt are non-negative
        assert np.all(R_ilt >= 0), \
            f"Scenario '{scenario_name}': R_ilt must be non-negative"
        
        # Check sum over time dimension (last dimension)
        R_ilt_sum = np.sum(R_ilt, axis=-1)
        assert np.allclose(R_ilt_sum, E_il), \
            f"Scenario '{scenario_name}': sum of R_ilt over time must equal E_il. " \
            f"Got {R_ilt_sum}, expected {E_il}"
    
    @staticmethod
    def distribution_statistics(R_ilt, scenario_name=""):
        """
        Calculate statistics for a staggered evacuation distribution.
        
        Parameters
        ----------
        R_ilt : np.ndarray
            Staggered evacuation distribution
        scenario_name : str, optional
            Name of scenario for reporting
            
        Returns
        -------
        stats : dict
            Dictionary containing:
            - total_evs: Total number of EVs
            - mean_time: Mean evacuation time
            - peak_time: Time period with maximum evacuations
            - peak_value: Maximum number of EVs in a single time period
            - time_to_80_percent: Time to evacuate 80% of EVs
            - coefficient_of_variation: CV of evacuation rates over time
        """
        # Sum over all locations and charge levels
        evacuation_profile = np.sum(R_ilt, axis=tuple(range(R_ilt.ndim - 1)))
        total_evs = np.sum(evacuation_profile)
        
        if total_evs == 0:
            return {
                "scenario": scenario_name,
                "total_evs": 0,
                "mean_time": 0,
                "peak_time": 0,
                "peak_value": 0,
                "time_to_80_percent": 0,
                "coefficient_of_variation": 0
            }
        
        # Mean evacuation time
        time_indices = np.arange(len(evacuation_profile))
        mean_time = np.sum(evacuation_profile * time_indices) / total_evs
        
        # Peak statistics
        peak_time = np.argmax(evacuation_profile)
        peak_value = np.max(evacuation_profile)
        
        # Time to 80% evacuation
        cumulative = np.cumsum(evacuation_profile)
        threshold_80 = 0.8 * total_evs
        time_to_80 = np.where(cumulative >= threshold_80)[0]
        time_to_80_percent = time_to_80[0] if len(time_to_80) > 0 else len(evacuation_profile)
        
        # Coefficient of variation
        std_dev = np.std(evacuation_profile)
        mean_evac_rate = np.mean(evacuation_profile)
        cv = std_dev / mean_evac_rate if mean_evac_rate > 0 else 0
        
        return {
            "scenario": scenario_name,
            "total_evs": int(total_evs),
            "mean_time": float(mean_time),
            "peak_time": int(peak_time),
            "peak_value": int(peak_value),
            "time_to_80_percent": int(time_to_80_percent),
            "coefficient_of_variation": float(cv)
        }
    
    @staticmethod
    def generate_staggered_starts_simple(E_il, T, alpha, beta, random_state=None):
        """
        Simple interface for generating a single staggered evacuation distribution.
        
        Parameters
        ----------
        E_il : int or array-like
            Total number of EVs to evacuate
        T : int
            Number of time periods
        alpha : float
            Beta distribution shape parameter α
        beta : float
            Beta distribution shape parameter β
        random_state : int, optional
            Random seed for reproducibility
            
        Returns
        -------
        R_ilt : np.ndarray
            Integer staggered evacuation distribution
        """
        return StaggeredEvacuationDistributions.beta_distribution(
            E_il=E_il,
            T=T,
            alpha=alpha,
            beta=beta,
            random_state=random_state
        )
