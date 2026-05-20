(load "bpc.lisp")

(defun parse-naive-json (str)
  (let* ((s1 (substitute #\( #\[ str))
         (s2 (substitute #\) #\] s1))
         (s3 (substitute #\Space #\, s2))
         (s4 (substitute #\Space #\: s3))
         (s5 (remove #\{ s4))
         (s6 (remove #\} s5))
         (s7 (remove #\" s6)))
    (read-from-string (concatenate 'string "(" s7 ")"))))

(defun main ()
  (loop
    (let ((input (read-line nil nil)))
      (unless input (return))
      (let* ((parsed (parse-naive-json input))
             ;; Note: The keys might be read as symbols depending on package.
             ;; If the string is "formula", `read` turns it into the symbol `FORMULA`.
             (formula-list (getf parsed 'formula))
             (seq-list (getf parsed 'sequence))
             (m (length formula-list))
             (formula (make-array m :element-type 'clause)))
        ;; build formula array
        (loop for i from 0 below m do
          (let* ((clause-list (nth i formula-list))
                 (len (length clause-list))
                 (clause (make-array len :element-type 'literal :initial-contents clause-list)))
            (setf (aref formula i) clause)))
        ;; build state
        (let* ((s0 (make-solver-state))
               (result-state (execute-macro-sequence s0 formula seq-list)))
          ;; CRITICAL FIX: Update the cardinality gap relative to the root ancestor s0
          (setf result-state (backtrack-to-ancestor result-state s0))
          ;; print json
          (format t "{\"status\": \"~A\", \"decisions\": ~D, \"props\": ~D, \"cardinality_gap\": ~D}~%"
                  (string-downcase (symbol-name (ss-status result-state)))
                  (ss-decisions result-state)
                  (ss-props result-state)
                  (ss-cardinality-gap result-state))
          (finish-output))))))

(main)