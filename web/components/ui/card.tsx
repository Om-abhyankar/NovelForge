'use client'

import * as React from 'react'
import { motion, type HTMLMotionProps } from 'framer-motion'

import { cn } from '@/lib/utils'

/**
 * Surfaces.
 *
 * `interactive` lifts the card 2px and deepens its shadow on hover. That, plus
 * the inset top highlight from `.surface-card`, is what makes a card feel like
 * an object with a light source rather than a div with a border.
 */
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  interactive?: boolean
  inset?: boolean
  glow?: boolean
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, interactive, inset, glow, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'surface-card relative',
        inset && 'bg-sunken shadow-none border-line/8',
        glow && 'shadow-glow',
        interactive && [
          'cursor-pointer transition-all duration-200 ease-out',
          'hover:-translate-y-0.5 hover:shadow-lg hover:border-line/16',
          'active:translate-y-0 active:shadow',
        ],
        className,
      )}
      {...props}
    />
  ),
)
Card.displayName = 'Card'

/** Animated variant, for lists that stagger in. */
export const MotionCard = React.forwardRef<
  HTMLDivElement,
  HTMLMotionProps<'div'> & { interactive?: boolean }
>(({ className, interactive, ...props }, ref) => (
  <motion.div
    ref={ref}
    className={cn('surface-card relative', className)}
    whileHover={interactive ? { y: -2 } : undefined}
    whileTap={interactive ? { y: 0, scale: 0.995 } : undefined}
    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
    {...props}
  />
))
MotionCard.displayName = 'MotionCard'

export const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex flex-col gap-1 p-4 pb-3', className)}
    {...props}
  />
))
CardHeader.displayName = 'CardHeader'

export const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn('text-md font-semibold text-ink', className)}
    {...props}
  />
))
CardTitle.displayName = 'CardTitle'

export const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn('text-sm text-ink-3', className)} {...props} />
))
CardDescription.displayName = 'CardDescription'

export const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-4 pt-0', className)} {...props} />
))
CardContent.displayName = 'CardContent'

export const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex items-center gap-2 p-4 pt-3', className)}
    {...props}
  />
))
CardFooter.displayName = 'CardFooter'

/**
 * A section heading used across panels: a very small, tracked, upper-case
 * label. One of the strongest signals of considered typography.
 */
export function SectionLabel({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'px-1 text-2xs font-semibold uppercase tracking-[0.14em] text-ink-4',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}
