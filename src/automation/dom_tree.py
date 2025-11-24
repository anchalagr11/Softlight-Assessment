from playwright.async_api import Page

async def get_page_accessibility_tree(page: Page, max_length: int = 50000) -> str:
    """
    Injects JavaScript to traverse the DOM and return a simplified text representation
    of interactive elements and important structure (headers, labels).
    Prioritizes active modals to ensure they aren't truncated.
    """
    js_code = """
    (() => {
        function isVisible(element) {
            if (!element.getBoundingClientRect) return false;
            const rect = element.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return false;
            const style = window.getComputedStyle(element);
            return style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
        }

        function getSafeText(node) {
            const tag = node.tagName.toLowerCase();
            let text = "";
            
            // Helper to check if text looks like a timestamp
            function isTimestamp(str) {
                return /^\d+\s*(min|h|d|w|mo|y)$/.test(str.trim());
            }
            
            // Helper to check if text is a generic prefix
            function isPrefix(str) {
                const trimmed = str.trim().toLowerCase();
                return ['project', 'issue', 'doc', 'document'].includes(trimmed);
            }
            
            // For buttons and links, use smarter extraction
            if (['a', 'button'].includes(tag)) {
                // Strategy 1: Look for semantic elements (strong, em, h1-h6) first
                const semanticSelectors = ['strong', 'b', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
                for (const sel of semanticSelectors) {
                    const elem = node.querySelector(sel);
                    if (elem && elem.innerText?.trim()) {
                        text = elem.innerText.trim();
                        break;
                    }
                }
                
                // Strategy 2: If no semantic element, extract text intelligently
                if (!text) {
                    // Get all text nodes from children
                    const textParts = [];
                    const walker = document.createTreeWalker(
                        node,
                        NodeFilter.SHOW_TEXT,
                        {
                            acceptNode: function(textNode) {
                                const trimmed = textNode.textContent.trim();
                                if (!trimmed) return NodeFilter.FILTER_REJECT;
                                // Skip timestamps and prefixes
                                if (isTimestamp(trimmed) || isPrefix(trimmed)) return NodeFilter.FILTER_REJECT;
                                return NodeFilter.FILTER_ACCEPT;
                            }
                        }
                    );
                    
                    while (walker.nextNode()) {
                        textParts.push(walker.currentNode.textContent.trim());
                    }
                    
                    // Use the longest text part (likely the main label)
                    if (textParts.length > 0) {
                        text = textParts.reduce((a, b) => a.length > b.length ? a : b);
                    }
                }
                
                // Strategy 3: Fallback to direct text nodes only
                if (!text) {
                    for (let child of node.childNodes) {
                        if (child.nodeType === Node.TEXT_NODE) {
                            const trimmed = child.textContent.trim();
                            if (trimmed && !isTimestamp(trimmed) && !isPrefix(trimmed)) {
                                text += trimmed + " ";
                            }
                        }
                    }
                    text = text.trim();
                }
            } else {
                // For other elements, extract only direct text nodes
                for (let child of node.childNodes) {
                    if (child.nodeType === Node.TEXT_NODE) {
                        text += child.textContent;
                    }
                }
                
                // If no direct text found, use innerText as fallback
                if (!text.trim()) {
                    text = node.innerText || "";
                }
            }
            
            // Clean up Linear-specific shortcuts and icons
            text = text.replace(/[▶⇧]/g, ''); 
            text = text.replace(/P then [A-Z]/g, '');
            text = text.replace(/(Ctrl|Alt|Shift|Cmd) [A-Z]/g, '');
            return text.replace(/\\s+/g, ' ').trim().slice(0, 50);
        }

        function isInteresting(node) {
            const tag = node.tagName.toLowerCase();
            const role = node.getAttribute('role');
            const ariaLabel = node.getAttribute('aria-label');
            
            // Interactive elements
            if (['a', 'button', 'input', 'textarea', 'select', 'details', 'summary'].includes(tag)) return true;
            if (['button', 'link', 'checkbox', 'menuitem', 'tab', 'textbox', 'combobox', 'listbox', 'dialog'].includes(role)) return true;
            if (node.getAttribute('contenteditable') === 'true') return true;
            
            // Structural/Informational
            if (/^h[1-6]$/.test(tag)) return true;
            if (tag === 'label') return true;
            
            // Elements with specific attributes that suggest interactivity
            if (node.onclick || node.getAttribute('onclick')) return true;
            if (tag === 'div' && (role === 'button' || node.className.includes('btn') || node.className.includes('button'))) return true;

            return false;
        }

        function traverse(root) {
            const output = [];
            const outputElements = new Set(); // Track elements we've already output
            
            const walker = document.createTreeWalker(
                root,
                NodeFilter.SHOW_ELEMENT,
                {
                    acceptNode: function(node) {
                        if (!isVisible(node)) return NodeFilter.FILTER_REJECT;
                        return NodeFilter.FILTER_ACCEPT;
                    }
                }
            );

            while (walker.nextNode()) {
                const node = walker.currentNode;
                
                // Skip if this element is inside an already-output link or button
                let hasOutputAncestor = false;
                let parent = node.parentElement;
                while (parent && parent !== root) {
                    if (outputElements.has(parent)) {
                        hasOutputAncestor = true;
                        break;
                    }
                    parent = parent.parentElement;
                }
                
                if (hasOutputAncestor) continue;
                
                if (isInteresting(node)) {
                    const tag = node.tagName.toLowerCase();
                    const text = getSafeText(node);
                    const role = node.getAttribute('role');
                    const ariaLabel = node.getAttribute('aria-label');
                    const placeholder = node.getAttribute('placeholder');
                    const name = node.getAttribute('name');
                    const id = node.id;
                    const type = node.getAttribute('type');
                    
                    let parts = [];
                    parts.push(`[${tag}]`);
                    
                    if (text) parts.push(`"${text}"`);
                    if (role) parts.push(`role="${role}"`);
                    if (ariaLabel) parts.push(`aria-label="${ariaLabel}"`);
                    if (placeholder) parts.push(`placeholder="${placeholder}"`);
                    if (name) parts.push(`name="${name}"`);
                    if (id) parts.push(`id="${id}"`);
                    if (type) parts.push(`type="${type}"`);
                    
                    if (tag === 'a' && node.getAttribute('href')) {
                        parts.push(`href="${node.getAttribute('href').slice(0, 30)}..."`);
                    }

                    output.push(parts.join(' '));
                    
                    // Mark links and buttons as output to skip their children
                    if (['a', 'button'].includes(tag)) {
                        outputElements.add(node);
                    }
                }
            }
            return output;
        }

        // 1. Try to find an active modal first
        const modalSelectors = [
            '[role="dialog"]',
            '[class*="modal"]',
            '[class*="dialog"]',
            '[aria-modal="true"]',
            'div[style*="z-index"][style*="fixed"]'
        ];
        
        let root = document.body;
        let prefix = "";
        
        for (const sel of modalSelectors) {
            const modals = document.querySelectorAll(sel);
            for (const modal of modals) {
                if (isVisible(modal) && modal.innerText.trim().length > 0) {
                    root = modal;
                    prefix = "!!! ACTIVE MODAL DETECTED - FOCUSING ON MODAL CONTENT !!!\\n";
                    break;
                }
            }
            if (root !== document.body) break;
        }

        const lines = traverse(root);
        return prefix + lines.join('\\n');
    })()
    """
    
    try:
        tree = await page.evaluate(js_code)
        if len(tree) > max_length:
            return tree[:max_length] + "\n... (truncated)"
        return tree
    except Exception as e:
        return f"Error generating accessibility tree: {str(e)}"
