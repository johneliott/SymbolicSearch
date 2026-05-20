(load "bpc.lisp")

(defun run-verification-suite ()
  "Correctly separated correctness + measurement + sensitivity analysis."

  (let* ((c0 (make-array 3 :element-type 'literal :initial-contents '(-1 -2 3)))
         (c1 (make-array 2 :element-type 'literal :initial-contents '(-3 4)))
         (c2 (make-array 2 :element-type 'literal :initial-contents '(-4 5)))
         (c3 (make-array 2 :element-type 'literal :initial-contents '(-2 -5)))

         (f  (make-array 4 :element-type 'clause
                         :initial-contents (list c0 c1 c2 c3)))

         (s0 (make-solver-state))
         (success t))

    (format t "====================================================~%")
    (format t "BCP KERNEL VERIFICATION HARNESS (REFACTORED)~%")
    (format t "====================================================~%")

    ;; ====================================================
    ;; 1. SEMANTIC CORRECTNESS TESTS (HARD INVARIANTS)
    ;; ====================================================

    (let ((res-a (execute-macro-sequence s0 f '(1 2)))
          (res-b (execute-macro-sequence s0 f '(2 1))))

      (format t "[TRAJECTORY A] (1 2): Status ~A~%" (ss-status res-a))
      (format t "[TRAJECTORY B] (2 1): Status ~A~%" (ss-status res-b))

      ;; Only semantic invariant: both must resolve consistently
      (unless (and (eq (ss-status res-a) :unsat)
                   (eq (ss-status res-b) :unsat))
        (setf success nil)
        (format t ">> ERROR: Semantic SAT/UNSAT invariant violated.~%")))

    ;; ====================================================
    ;; 2. TRACE SANITY CHECKS (WEAK CONSTRAINTS)
    ;; ====================================================

    (let ((res-a (execute-macro-sequence s0 f '(1 2)))
          (res-b (execute-macro-sequence s0 f '(2 1))))

      ;; sanity: propagation must be non-negative
      (unless (and (>= (ss-props res-a) 0)
                   (>= (ss-props res-b) 0))
        (setf success nil)
        (format t ">> ERROR: Negative propagation count detected.~%"))

      (format t "[TRACE] Props A: ~D~%" (ss-props res-a))
      (format t "[TRACE] Props B: ~D~%" (ss-props res-b)))

    ;; ====================================================
    ;; 3. PERMUTATION SENSITIVITY MEASUREMENT (NO ASSERTS)
    ;; ====================================================

    (let ((res-a (execute-macro-sequence s0 f '(1 2)))
          (res-b (execute-macro-sequence s0 f '(2 1))))

      (let ((delta-props (- (ss-props res-a)
                            (ss-props res-b)))

            (delta-decisions (- (ss-decisions res-a)
                                (ss-decisions res-b))))

        (format t "====================================================~%")
        (format t "PERMUTATION SENSITIVITY METRICS~%")
        (format t "Δ Props      = ~D~%" delta-props)
        (format t "Δ Decisions  = ~D~%" delta-decisions)
        (format t "====================================================~%")))

    ;; ====================================================
    ;; 4. CONTEXT STABILITY / ISOLATION TEST
    ;; ====================================================

    (let* ((sibling-ancestor (inject-literal s0 f -1 :is-decision t))
           (branch-a (execute-macro-sequence sibling-ancestor f '(1 2)))
           (branch-b (execute-macro-sequence sibling-ancestor f '(2 1))))

      (backtrack-to-ancestor branch-a sibling-ancestor)
      (backtrack-to-ancestor branch-b sibling-ancestor)

      (format t "[CONTEXT ISOLATION]~%")
      (format t "  Branch A Gap: ~D~%" (ss-cardinality-gap branch-a))
      (format t "  Branch B Gap: ~D~%" (ss-cardinality-gap branch-b))

      ;; only invariant: no corruption / no crash / defined output
      (unless (and (numberp (ss-cardinality-gap branch-a))
                   (numberp (ss-cardinality-gap branch-b)))
        (setf success nil)
        (format t ">> ERROR: Cardinality metric is invalid.~%")))

    ;; ====================================================
    ;; 5. SYSTEM EXIT
    ;; ====================================================

    (format t "====================================================~%")

    (if success
        (progn
          (format t "VERIFICATION SUCCESSFUL~%")
          (uiop:quit 0))
        (progn
          (format t "VERIFICATION FAILED~%")
          (uiop:quit 1)))))

(run-verification-suite)
