import { cloneElement, useMemo, useState } from "react";
import {
  // Placement,
  offset,
  flip,
  shift,
  autoUpdate,
  useFloating,
  useInteractions,
  useHover,
  useFocus,
  useRole,
  useDismiss,
} from "@floating-ui/react-dom-interactions";
import { mergeRefs } from "react-merge-refs";

const Tooltip = ({
  children,
  content,
  label,
  placement,
  classes = "Tooltip",
}) => {
  const [open, setOpen] = useState(false);

  const { x, y, reference, floating, strategy, context } = useFloating({
    placement,
    open,
    onOpenChange: setOpen,
    middleware: [offset(5), flip(), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
  });

  const { getReferenceProps, getFloatingProps } = useInteractions([
    useHover(context),
    useFocus(context),
    useRole(context, { role: "tooltip" }),
    useDismiss(context),
  ]);

  // Preserve the consumer's ref
  const ref = useMemo(
    () => mergeRefs([reference, children.ref]),
    [reference, children]
  );

  return (
    <>
      {cloneElement(children, getReferenceProps({ ref, ...children.props }))}
      {open && (
        <div
          ref={floating}
          className={classes}
          style={{
            position: strategy,
            top: y ?? 0,
            left: x ?? 0,
            zIndex: 99999,
          }}
          {...getFloatingProps()}
        >
          {content ?? label}
        </div>
      )}
    </>
  );
};

export { Tooltip };
