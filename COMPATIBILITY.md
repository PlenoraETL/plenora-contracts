# Public compatibility policy

Compatibility is evaluated from the point of view of a conforming external
consumer.

## Compatible changes

A change is compatible only when an existing conforming consumer can continue
to invoke the same operation and interpret the result with the same meaning.

Typical compatible changes are:

- adding an optional field whose absence preserves the previous behavior;
- exposing a new operation under a new stable identifier;
- adding a new public surface to an existing operation;
- adding an unavailable capability with an explicit reason;
- clarifying prose without changing accepted data or semantics.

## Incompatible changes

The following are incompatible:

- removing or renaming an operation, required field or public symbol;
- changing the meaning, type, units or default of a field;
- changing a success into a partial outcome, or an acknowledged partial
  outcome into success;
- weakening remote-effect or retry information;
- silently replacing one output contract or content type with another;
- changing CLI stream selection or exit-code projection;
- dropping a supported SDK runtime version outside the component's declared
  compatibility policy;
- changing a closed enumeration without an explicit version transition.

An incompatible change requires a new public contract version. A component may
temporarily expose old and new versions together and advertise both through
capability discovery.

## Operation evolution

Operation identity and operation contract version are independent from package
and component release versions. A component patch or minor release may expose a
new compatible operation. It must not change an existing operation contract
incompatibly without incrementing that contract version.

## Consumer behavior

Consumers must select only advertised operations and versions. They must ignore
unknown optional fields where the enclosing schema permits them and must fail
closed on unknown required contract versions.

## Schema immutability

A versioned JSON Schema may be changed in place only when the edit cannot alter
whether an existing instance validates. Otherwise a new schema identifier and
file are required.
