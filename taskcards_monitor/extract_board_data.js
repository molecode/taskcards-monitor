() => {
    const data = {
        lists: [],
        cards: []
    };

    // Find all card containers (each contains one list and its cards)
    const containers = document.querySelectorAll('.card-container');

    containers.forEach((container, listIndex) => {
        // Find the board-list (column header) within this container
        const listEl = container.querySelector('.board-list');
        if (!listEl) return;

        const listId = listEl.getAttribute('data-list-id') ||
                      listEl.getAttribute('id') ||
                      `list-${listIndex}`;

        // Find list title
        let listName = '';
        const headerEl = listEl.querySelector('.board-list-header');
        if (headerEl) {
            // Look for .text-h6 > .contenteditable
            const h6 = headerEl.querySelector('.text-h6');
            if (h6) {
                const editable = h6.querySelector('.contenteditable');
                if (editable) {
                    listName = editable.textContent.trim();
                }
            }
        }

        data.lists.push({
            id: listId,
            name: listName,
            position: listIndex,
            color: null
        });

        // Find the list-content-container (sibling of board-list)
        const contentContainer = container.querySelector('.list-content-container');
        if (!contentContainer) return;

        // Find all cards in this container
        const cards = contentContainer.querySelectorAll('.board-card');

        cards.forEach((cardEl, cardIndex) => {
            const cardId = cardEl.getAttribute('data-card-id') ||
                          cardEl.getAttribute('id') ||
                          `card-${listId}-${cardIndex}`;

            // Find card title from header
            let cardTitle = '';
            const cardHeader = cardEl.querySelector('.board-card-header');
            if (cardHeader) {
                const editable = cardHeader.querySelector('.contenteditable');
                if (editable) {
                    cardTitle = editable.textContent.trim();
                } else {
                    cardTitle = cardHeader.textContent.trim();
                }
            }

            // If no title found, use card content
            if (!cardTitle) {
                const cardContent = cardEl.querySelector('.board-card-content');
                if (cardContent) {
                    cardTitle = cardContent.textContent.trim().substring(0, 100);
                }
            }

            // Fallback to any text in the card
            if (!cardTitle) {
                cardTitle = cardEl.textContent.trim().substring(0, 100);
            }

            data.cards.push({
                id: cardId,
                title: cardTitle,
                description: '',
                created: null,
                modified: null,
                kanbanPosition: {
                    listId: listId,
                    position: cardIndex
                }
            });
        });
    });

    return data;
}
