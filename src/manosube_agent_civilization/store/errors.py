"""Fail-closed State Store errors."""

class StoreError(RuntimeError): pass
class BoundaryError(StoreError): pass
class StateNotFoundError(StoreError): pass
class AlreadyInitializedError(StoreError): pass
class StaleStateError(StoreError): pass
class RevisionError(StoreError): pass
class TransactionConflictError(StoreError): pass
class RecordConflictError(StoreError): pass
class CorruptStoreError(StoreError): pass
class SimulatedCrash(StoreError): pass
