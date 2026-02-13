import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { Controller, FormProvider, useFormContext } from "react-hook-form"
import { cn } from "@/lib/utils"
import { Label } from "@/components/ui/label"

const Form = FormProvider

const FormFieldContext = React.createContext({})
function FormField({ ...props }) {
  return (<FormFieldContext.Provider value={{ name: props.name }}><Controller {...props} /></FormFieldContext.Provider>)
}

const FormItemContext = React.createContext({})
function useFormField() {
  const fieldContext = React.useContext(FormFieldContext)
  const itemContext = React.useContext(FormItemContext)
  const { getFieldState, formState } = useFormContext()
  const fieldState = getFieldState(fieldContext.name, formState)
  if (!fieldContext) throw new Error("useFormField should be used within <FormField>")
  const { id } = itemContext
  return { id, name: fieldContext.name, formItemId: `${id}-form-item`, formDescriptionId: `${id}-form-item-description`, formMessageId: `${id}-form-item-message`, ...fieldState }
}

function FormItem({ className, ...props }) {
  const id = React.useId()
  return (<FormItemContext.Provider value={{ id }}><div data-slot="form-item" className={cn("grid gap-2", className)} {...props} /></FormItemContext.Provider>)
}

function FormLabel({ className, ...props }) {
  const { formItemId } = useFormField()
  return <Label data-slot="form-label" className={className} htmlFor={formItemId} {...props} />
}

function FormControl({ ...props }) {
  const { formItemId, formDescriptionId, formMessageId } = useFormField()
  return (<Slot data-slot="form-control" id={formItemId} aria-describedby={`${formDescriptionId} ${formMessageId}`} {...props} />)
}

function FormMessage({ className, ...props }) {
  const { formMessageId } = useFormField()
  const body = props.children
  if (!body) return null
  return (<p data-slot="form-message" id={formMessageId} className={cn("text-destructive text-sm", className)} {...props}>{body}</p>)
}

export { useFormField, Form, FormItem, FormLabel, FormControl, FormMessage, FormField }
