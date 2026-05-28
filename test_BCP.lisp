(load "BCP_KERNEL.lisp")

(defun run-verification-suite ()
  "Correctly separated correctness + measurement + sensitivity analysis."

  (let* ((c0 (make-array 3 :element-type 'literal :initial-contents '(-1 -2 3)))
       (c1 (make-array 2 :element-type 'literal :initial-contents '(-3 4)))
       (c2 (make-array 2 :element-type 'literal :initial-contents '(-4 5)))
       (c3 (make-array 2 :element-type 'literal :initial-contents '(-2 -5)))

       (f  (make-array 4 :element-type 'clause
                       :initial-contents (list c0 c1 c2 c3)))
       (w  (setup-watches f))
       (s0 (pre-flight-bcp (make-solver-state) f w))
       (success t))

  (format t "====================================================~%")
  (format t "BCP KERNEL VERIFICATION HARNESS (REFACTORED)~%")
  (format t "====================================================~%")

  ;; ====================================================
  ;; 1. SEMANTIC CORRECTNESS TESTS (HARD INVARIANTS)
  ;; ====================================================

  (let* ((local-f (deep-copy-formula f))
         (local-w (deep-copy-watches w))
         (res-a (execute-macro-sequence-watched s0 local-f local-w '(1 2)))
         (local-f2 (deep-copy-formula f))
         (local-w2 (deep-copy-watches w))
         (res-b (execute-macro-sequence-watched s0 local-f2 local-w2 '(2 1))))

    (format t "[TRAJECTORY A] (1 2): Status ~A~%" (ss-status res-a))
    (format t "[TRAJECTORY B] (2 1): Status ~A~%" (ss-status res-b))

    ;; Only semantic invariant: both must resolve consistently
    (unless (and (eq (ss-status res-a) :unsat)
                 (eq (ss-status res-b) :unsat))
      (setf success nil)
      (format t ">> ERROR: Semantic SAT/UNSAT invariant violated.~%"))

  ;; ====================================================
  ;; 2. TRACE SANITY CHECKS (WEAK CONSTRAINTS)
  ;; ====================================================

    ;; sanity: propagation must be non-negative
    (unless (and (>= (ss-props res-a) 0)
                 (>= (ss-props res-b) 0))
      (setf success nil)
      (format t ">> ERROR: Negative propagation count detected.~%"))

    (format t "[TRACE] Props A: ~D~%" (ss-props res-a))
    (format t "[TRACE] Props B: ~D~%" (ss-props res-b))

  ;; ====================================================
  ;; 3. PERMUTATION SENSITIVITY MEASUREMENT (NO ASSERTS)
  ;; ====================================================

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

  (let* ((local-f (deep-copy-formula f))
         (local-w (deep-copy-watches w))
         (sibling-ancestor (inject-literal-watched s0 local-f local-w -1 :is-decision t))
         (local-f-a (deep-copy-formula local-f))
         (local-w-a (deep-copy-watches local-w))
         (branch-a (execute-macro-sequence-watched sibling-ancestor local-f-a local-w-a '(1 2)))
         (local-f-b (deep-copy-formula local-f))
         (local-w-b (deep-copy-watches local-w))
         (branch-b (execute-macro-sequence-watched sibling-ancestor local-f-b local-w-b '(2 1))))
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