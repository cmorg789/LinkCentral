import { useEffect, useRef } from 'react';
import { EditorView, basicSetup } from 'codemirror';
import { EditorState } from '@codemirror/state';
import { sql } from '@codemirror/lang-sql';
import { oneDark } from '@codemirror/theme-one-dark';
import { cn } from '@/lib/cn';

interface SqlEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  readOnly?: boolean;
  height?: string;
  className?: string;
  darkMode?: boolean;
}

export function SqlEditor({
  value,
  onChange,
  placeholder,
  readOnly = false,
  height = '200px',
  className,
  darkMode = false,
}: SqlEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<EditorView | null>(null);
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);

  // Keep refs in sync
  valueRef.current = value;
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!containerRef.current) return;

    const extensions = [
      basicSetup,
      sql(),
      EditorView.lineWrapping,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          const newValue = update.state.doc.toString();
          if (newValue !== valueRef.current) {
            onChangeRef.current(newValue);
          }
        }
      }),
    ];

    if (darkMode) {
      extensions.push(oneDark);
    }

    if (readOnly) {
      extensions.push(EditorState.readOnly.of(true));
    }

    if (placeholder) {
      extensions.push(EditorView.contentAttributes.of({ 'data-placeholder': placeholder }));
    }

    const state = EditorState.create({
      doc: value,
      extensions,
    });

    const view = new EditorView({
      state,
      parent: containerRef.current,
    });

    editorRef.current = view;

    return () => {
      view.destroy();
      editorRef.current = null;
    };
    // Only recreate editor on mount or when readOnly/darkMode changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readOnly, darkMode]);

  // Update editor content when value changes externally
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    const currentValue = editor.state.doc.toString();
    if (currentValue !== value) {
      editor.dispatch({
        changes: {
          from: 0,
          to: currentValue.length,
          insert: value,
        },
      });
    }
  }, [value]);

  return (
    <div
      ref={containerRef}
      className={cn(
        'border rounded-md overflow-hidden',
        darkMode ? 'bg-[#282c34]' : 'bg-white',
        className
      )}
      style={{ height }}
    />
  );
}
