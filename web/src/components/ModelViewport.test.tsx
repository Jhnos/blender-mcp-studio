import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ModelViewport } from './ModelViewport'

const IMAGE_URL = 'data:image/png;base64,viewport'

describe('ModelViewport', () => {
  it('uses the full work area and exposes the current zoom', () => {
    render(<ModelViewport imageUrl={IMAGE_URL} loading={false} />)

    expect(screen.getByRole('img', { name: 'Blender 模型預覽' })).toHaveClass('h-full', 'w-full')
    expect(screen.getByText('預覽倍率 100%')).toBeInTheDocument()
  })

  it('zooms the model preview in useful fixed steps', () => {
    render(<ModelViewport imageUrl={IMAGE_URL} loading={false} />)

    fireEvent.click(screen.getByRole('button', { name: '放大預覽' }))

    expect(screen.getByText('預覽倍率 125%')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Blender 模型預覽' })).toHaveStyle({
      transform: 'scale(1.25)',
    })
  })

  it('keeps zoom within a readable range and can reset it', () => {
    render(<ModelViewport imageUrl={IMAGE_URL} loading={false} />)

    const zoomOut = screen.getByRole('button', { name: '縮小預覽' })
    fireEvent.click(zoomOut)
    expect(screen.getByText('預覽倍率 75%')).toBeInTheDocument()
    expect(zoomOut).toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: '重設預覽倍率' }))
    expect(screen.getByText('預覽倍率 100%')).toBeInTheDocument()

    const zoomIn = screen.getByRole('button', { name: '放大預覽' })
    for (let index = 0; index < 4; index += 1) fireEvent.click(zoomIn)
    expect(screen.getByText('預覽倍率 200%')).toBeInTheDocument()
    expect(zoomIn).toBeDisabled()
  })

  it('enters a focused preview and exits with Escape', () => {
    render(<ModelViewport imageUrl={IMAGE_URL} loading={false} />)

    fireEvent.click(screen.getByRole('button', { name: '進入專注預覽' }))
    expect(screen.getByRole('button', { name: '離開專注預覽' })).toBeInTheDocument()
    expect(screen.getByTestId('model-viewport')).toHaveAttribute('data-focused', 'true')
    expect(screen.getByTestId('model-viewport')).toHaveClass('fixed', 'inset-0')
    expect(screen.getByTestId('model-viewport')).not.toHaveClass('relative')

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.getByRole('button', { name: '進入專注預覽' })).toBeInTheDocument()
    expect(screen.getByTestId('model-viewport')).toHaveAttribute('data-focused', 'false')
  })
})
