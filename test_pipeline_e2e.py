import os
import unittest
import subprocess

# Import your live, unmodified production engine machinery
from harness import LispKernel, evaluate_orbit, summarize

class TestLiveSATDeformationPipeline(unittest.TestCase):
    
    def setUp(self):
        """Verify workspace integrity and initialize realistic test inputs."""
        # Ensure production files exist in the path before attempting to run
        self.assertTrue(os.path.exists("BCP_KERNEL.lisp"), "Production 'BCP_KERNEL.lisp' not found in working directory.")
        self.assertTrue(os.path.exists("runner.lisp"), "Production 'runner.lisp' not found in working directory.")
        
        # A tiny, valid horn-like formula: (x1 v x2) ^ (~x1 v x3)
        self.production_formula = [[1, 2], [-1, 3]]
        
        # A realistic macro decision sequence to execute post-stabilization
        self.production_sequence = [2, 3]
        
        # A clean, non-conflicting background context
        self.valid_context = [1]

    def test_01_live_kernel_io_loop(self):
        """Verify raw pipe streaming and JSON parsing against the live SBCL process."""
        # Initialize the real kernel targeting your actual runner file
        kernel = LispKernel(script_path="runner.lisp")
        
        try:
            response = kernel.run_sequence(
                formula=self.production_formula,
                seq=self.production_sequence,
                context=self.valid_context
            )
            
            # Validate structural integrity of your actual Lisp JSON output strings
            self.assertIsInstance(response, dict, "Lisp output failed to deserialize into a Python dictionary.")
            self.assertIn("status", response)
            self.assertIn("decisions", response)
            self.assertIn("props", response)
            self.assertIn("cardinality_gap", response)
            
            # Ensure type safety across the IPC boundary
            self.assertIsInstance(response["decisions"], int)
            self.assertIsInstance(response["props"], int)
            
        finally:
            kernel.close()

    def test_02_live_orbit_evaluation_and_aggregation(self):
        """Verify the full perturbation orbit evaluation loop and statistical compiler."""
        kernel = LispKernel(script_path="runner.lisp")
        
        try:
            # Run the actual orbit evaluation loop with a low perturbation count (N) for speed
            base, deltas = evaluate_orbit(
                kernel=kernel,
                formula=self.production_formula,
                base_seq=self.production_sequence,
                context=self.valid_context,
                N=3
            )
            
            # Verify the core tracking state records correctly
            self.assertIsInstance(base, dict)
            self.assertIsInstance(deltas, list)
            
            # If the context stabilized without a conflict, compile metrics
            if base["status"] != "init_conflict" and len(deltas) > 0:
                first_node = deltas[0]
                self.assertIn("tau", first_node)
                self.assertIn("props", first_node)
                
                # Pass real live data directly into your statistical summarizer
                stats = summarize(deltas)
                self.assertIn("tau_mean", stats)
                self.assertIn("tau_var", stats)
                self.assertIn("props_delta_var", stats)
                
        finally:
            kernel.close()

    def test_03_live_pre_flight_conflict_rejection(self):
        """Verify that an inherently broken context forces a quick exit in production."""
        kernel = LispKernel(script_path="runner.lisp")
        
        # Force an obvious, direct contradiction into the context tracking array
        contradictory_context = [10, -10]
        
        try:
            base, deltas = evaluate_orbit(
                kernel=kernel,
                formula=self.production_formula,
                base_seq=self.production_sequence,
                context=contradictory_context,
                N=2
            )
            
            # Assert that the catch loop blocks the sequence run and outputs the correct failure token
            self.assertEqual(base["status"], "init_conflict")
            self.assertEqual(len(deltas), 0, "Deltas were populated despite an invalid root context state.")
            
        finally:
            kernel.close()
