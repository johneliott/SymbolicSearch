(require 'asdf)

(deftype literal () 'fixnum)
(deftype clause  () '(simple-array literal (*)))
(deftype formula () '(simple-array clause (*)))

(defstruct (solver-state (:conc-name ss-))
  (trail          '()  :type list)
  (assignment     (make-array 20000 :element-type '(unsigned-byte 2) :initial-element 0) :type (simple-array (unsigned-byte 2) (*)))
  (status         :SAT :type (member :SAT :UNSAT :UNDEF))
  (decisions      0    :type fixnum)
  (props          0    :type fixnum)
  (cardinality-gap 0   :type fixnum))

(defun copy-solver-state-safe (state)
  (let ((new-state (copy-structure state)))
    (setf (ss-assignment new-state) (copy-seq (ss-assignment state)))
    new-state))

(defvar *max-var* 10000)

(defun lit-to-idx (lit)
  (+ lit *max-var*))

(defstruct prop-queue
  (items (make-array 10000 :element-type 'literal :adjustable t :fill-pointer 0))
  (head 0))

(defun push-queue (q lit)
  (vector-push-extend lit (prop-queue-items q)))

(defun pop-queue (q)
  (if (< (prop-queue-head q) (length (prop-queue-items q)))
      (let ((lit (aref (prop-queue-items q) (prop-queue-head q))))
        (incf (prop-queue-head q))
        lit)
      nil))

(defun eval-literal (lit assignment)
  (let ((val (aref assignment (abs lit))))
    (if (= val 0)
        :unknown
        (if (> lit 0)
            (if (= val 1) :true :false)
            (if (= val 1) :false :true)))))

(defun deep-copy-formula (formula)
  (let* ((len (length formula))
         (new-f (make-array len :element-type 'clause)))
    (loop for i from 0 below len do
      (setf (aref new-f i) (copy-seq (aref formula i))))
    new-f))

(defun deep-copy-watches (watches)
  (let* ((len (length watches))
         (new-w (make-array len :initial-element '())))
    (loop for i from 0 below len do
      (setf (aref new-w i) (copy-list (aref watches i))))
    new-w))

(defun setup-watches (formula)
  (let ((watches (make-array (1+ (* 2 *max-var*)) :initial-element '())))
    (loop for i from 0 below (length formula) do
      (let ((clause (aref formula i)))
        (when (>= (length clause) 2)
          (push i (aref watches (lit-to-idx (aref clause 0))))
          (push i (aref watches (lit-to-idx (aref clause 1)))))))
    watches))

(defun propagate-watched (state formula watches q)
  (loop
    (let ((p (pop-queue q)))
      (unless p (return state))
      (let* ((false-lit (- p))
             (idx (lit-to-idx false-lit))
             (watch-list (aref watches idx))
             (new-watch-list '()))
        (setf (aref watches idx) '())
        
        (let ((conflict nil))
          (loop for c-idx in watch-list do
            (if conflict
                (push c-idx new-watch-list)
                (let ((clause (aref formula c-idx)))
                  (when (= (aref clause 0) false-lit)
                    (setf (aref clause 0) (aref clause 1))
                    (setf (aref clause 1) false-lit))
                  
                  (if (eq (eval-literal (aref clause 0) (ss-assignment state)) :true)
                      (push c-idx new-watch-list)
                      (let ((found-new nil))
                        (loop for k from 2 below (length clause) do
                          (let ((lit-k (aref clause k)))
                            (unless (eq (eval-literal lit-k (ss-assignment state)) :false)
                              (setf (aref clause 1) lit-k)
                              (setf (aref clause k) false-lit)
                              (push c-idx (aref watches (lit-to-idx lit-k)))
                              (setf found-new t)
                              (return))))
                        (unless found-new
                          (push c-idx new-watch-list)
                          (let ((other-val (eval-literal (aref clause 0) (ss-assignment state))))
                            (cond
                              ((eq other-val :false)
                               (setf conflict t))
                              ((eq other-val :unknown)
                               (let ((forced-lit (aref clause 0)))
                                 (incf (ss-props state))
                                 (push forced-lit (ss-trail state))
                                 (setf (aref (ss-assignment state) (abs forced-lit))
                                       (if (> forced-lit 0) 1 2))
                                 (push-queue q forced-lit)))))))))))
          (setf (aref watches idx) (nconc new-watch-list (aref watches idx)))
          (when conflict
            (setf (ss-status state) :unsat)
            (return state)))))))

(defun inject-literal-watched (state formula watches lit &key is-decision)
  (let ((new-state (copy-solver-state-safe state)))
    (when is-decision
      (incf (ss-decisions new-state)))
    (push lit (ss-trail new-state))
    (setf (aref (ss-assignment new-state) (abs lit))
          (if (> lit 0) 1 2))
    (let ((q (make-prop-queue)))
      (push-queue q lit)
      (propagate-watched new-state formula watches q))))

(defun execute-macro-sequence-watched (state formula watches seq)
  (let ((current state))
    (dolist (lit seq current)
      (when (eq (ss-status current) :unsat)
        (return current))
      (setf current (inject-literal-watched current formula watches lit :is-decision t)))))

(defun backtrack-to-ancestor (current ancestor)
  (let ((gap (abs (- (length (ss-trail current)) (length (ss-trail ancestor))))))
    (setf (ss-cardinality-gap current) gap)
    current))

(defun pre-flight-bcp (state formula watches)
  (let ((q (make-prop-queue)))
    (dolist (lit (ss-trail state))
      (push-queue q lit))
    (loop for i from 0 below (length formula) do
      (let ((clause (aref formula i)))
        (when (= (length clause) 1)
          (let* ((lit (aref clause 0))
                 (val (eval-literal lit (ss-assignment state))))
            (cond
              ((eq val :false)
               (setf (ss-status state) :unsat))
              ((eq val :unknown)
               (incf (ss-props state))
               (push lit (ss-trail state))
               (setf (aref (ss-assignment state) (abs lit))
                     (if (> lit 0) 1 2))
               (push-queue q lit)))))))
    (if (eq (ss-status state) :unsat)
        state
        (propagate-watched state formula watches q))))
