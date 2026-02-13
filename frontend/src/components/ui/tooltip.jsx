import * as React from "react"
import * as TooltipPrimitive from "@radix-ui/react-tooltip"
import { cn } from "@/lib/utils"

function TooltipProvider({ delayDuration = 0, ...props }) {
  return (<TooltipPrimitive.Provider data-slot="tooltip-provider" delayDuration={delayDuration} {...props} />)
}
function Tooltip({ ...props }) {
  return (<TooltipPrimitive.Root data-slot="tooltip" {...props} />)
}
function TooltipTrigger({ ...props }) {
  return (<TooltipPrimitive.Trigger data-slot="tooltip-trigger" {...props} />)
}
function TooltipContent({ className, sideOffset = 4, children, ...props }) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content data-slot="tooltip-content" sideOffset={sideOffset}
        className={cn("bg-primary text-primary-foreground animate-in fade-in-0 zoom-in-95 z-50 w-fit rounded-md px-3 py-1.5 text-xs", className)}
        {...props}
      >{children}<TooltipPrimitive.Arrow className="fill-primary" /></TooltipPrimitive.Content>
    </TooltipPrimitive.Portal>
  )
}

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider }
