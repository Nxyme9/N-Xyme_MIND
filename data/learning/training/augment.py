"""
Data augmentation for RosEnna Trainer.
Generates paraphrases and hard negatives for contrastive learning.
"""
from torch.utils.data import Dataset

import random
from typing import List, Tuple, Dict


# Synonym mappings for rule-based paraphrase generation
SYNONYMS = {
    'find': ['search', 'locate', 'get', 'fetch', 'look for'],
    'get': ['fetch', 'obtain', 'retrieve', 'grab', 'take'],
    'create': ['make', 'build', 'generate', 'add', 'new'],
    'delete': ['remove', 'erase', 'clear', 'wipe', 'purge'],
    'read': ['view', 'show', 'display', 'open', 'load'],
    'write': ['save', 'store', 'put', 'add', 'record'],
    'edit': ['modify', 'change', 'update', 'alter', 'fix'],
    'run': ['execute', 'start', 'launch', 'begin', 'trigger'],
    'install': ['setup', 'add', 'put', 'enable', 'deploy'],
    'search': ['find', 'look', 'query', 'filter', 'seek'],
    'clear': ['reset', 'clean', 'wipe', 'empty', 'remove'],
    'end': ['close', 'stop', 'finish', 'terminate', 'quit'],
    'commit': ['save', 'submit', 'push', 'record', 'log'],
    'clone': ['copy', 'duplicate', 'fetch', 'download', 'get'],
    'push': ['send', 'upload', 'publish', 'submit', 'commit'],
    'pull': ['fetch', 'download', 'get', 'merge', 'update'],
    'list': ['show', 'display', 'view', 'ls', 'enumerate'],
    'query': ['search', 'ask', 'request', 'fetch', 'get'],
    'process': ['handle', 'run', 'execute', 'do', 'work on'],
    'fetch': ['get', 'retrieve', 'download', 'obtain', 'pull'],
}


def _synonym_substitution(query: str) -> str:
    """Replace words with synonyms."""
    words = query.split()
    result = []
    for word in words:
        word_lower = word.lower()
        if word_lower in SYNONYMS:
            synonyms = SYNONYMS[word_lower]
            replacement = random.choice(synonyms)
            if word[0].isupper():
                replacement = replacement.capitalize()
            result.append(replacement)
        else:
            result.append(word)
    return ' '.join(result)


def _word_reorder(query: str) -> str:
    """Reorder words randomly while maintaining basic structure."""
    words = query.split()
    if len(words) <= 2:
        return query

    # Keep first and last word, shuffle middle
    middle = words[1:-1]
    random.shuffle(middle)
    return words[0] + ' ' + ' '.join(middle) + ' ' + words[-1]


def _modal_verb_variant(query: str) -> str:
    """Convert between modal verb forms."""
    query_lower = query.lower()

    modal_mappings = [
        (['can you', 'could you', 'would you'], 'please'),
        (['please'], 'can you'),
        (['can i', 'could i', 'would it be possible to'], 'let me'),
        (['let me'], 'can i'),
    ]

    for forms, replacement in modal_mappings:
        for form in forms:
            if form in query_lower:
                return query_lower.replace(form, replacement, 1).capitalize()

    # Add/remove modal verbs
    if not any(m in query_lower for m in ['can', 'could', 'would', 'please']):
        prefixes = ['Can you ', 'Please ', 'Could you ']
        return random.choice(prefixes) + query_lower

    return query


def _imperative_variant(query: str) -> str:
    """Convert to imperative or vice versa."""
    query_lower = query.lower()

    # Remove subject pronouns to make imperative
    imperatives = ['delete', 'remove', 'find', 'get', 'create', 'make', 'show', 'list']
    for imp in imperatives:
        if query_lower.startswith(f'i want to {imp}'):
            return query_lower.replace(f'i want to {imp}', f'{imp}', 1).capitalize()
        if query_lower.startswith(f'i need to {imp}'):
            return query_lower.replace(f'i need to {imp}', f'{imp}', 1).capitalize()

    # Add "please" for politeness
    if not query_lower.startswith('please'):
        return 'Please ' + query_lower

    return query


def generate_paraphrases(query: str, n: int = 10) -> List[str]:
    """
    Generate n paraphrase variations of the query.

    Uses rule-based transformations:
    - Synonym substitution
    - Word reordering
    - Modal verb variants
    - Imperative variants

    Args:
        query: Original query string
        n: Number of paraphrases to generate

    Returns:
        List of n paraphrase strings
    """
    if not query or not query.strip():
        return []

    paraphrases = []
    methods = [
        _synonym_substitution,
        _word_reorder,
        _modal_verb_variant,
        _imperative_variant,
    ]

    # Generate n paraphrases using different methods
    for i in range(n):
        method = methods[i % len(methods)]
        para = method(query)
        if para and para != query:
            paraphrases.append(para)
        else:
            # Fallback: add prefix/suffix
            variants = [
                f"Could you {query.lower()}?",
                f"Please {query.lower()}",
                f"I need to {query.lower()}",
            ]
            paraphrases.append(random.choice(variants))

    # Ensure we have exactly n unique paraphrases
    paraphrases = list(set(paraphrases))[:n]

    # If we don't have enough, generate more
    while len(paraphrases) < n:
        method = random.choice(methods)
        para = method(query)
        if para and para not in paraphrases:
            paraphrases.append(para)

    return paraphrases[:n]


def _get_confusable_tools(tool: str, all_tools: List[str]) -> List[str]:
    """
    Get tools that are most confusable with the given tool.
    Based on name/description similarity.
    """
    confusable = {
        'memory_search': ['memory_write', 'search_files', 'file_read'],
        'memory_write': ['memory_search', 'file_write', 'database_query'],
        'safe_delete': ['empty_trash', 'project_clean', 'context_prune'],
        'session_end': ['context_prune', 'safe_delete'],
        'context_prune': ['session_end', 'project_clean', 'empty_trash'],
        'project_clean': ['safe_delete', 'context_prune', 'empty_trash'],
        'empty_trash': ['safe_delete', 'project_clean'],
        'file_read': ['file_edit', 'directory_list', 'search_files'],
        'file_write': ['file_edit', 'directory_create', 'database_query'],
        'file_edit': ['file_read', 'file_write', 'code_run'],
        'directory_create': ['directory_list', 'file_write'],
        'directory_list': ['directory_create', 'file_read', 'search_files'],
        'git_clone': ['git_pull', 'git_commit', 'git_push'],
        'git_commit': ['git_push', 'git_pull', 'git_clone'],
        'git_push': ['git_commit', 'git_pull'],
        'git_pull': ['git_clone', 'git_push', 'git_commit'],
        'search_files': ['memory_search', 'directory_list', 'file_read'],
        'run_command': ['code_run', 'install_package'],
        'install_package': ['run_command', 'code_run'],
        'web_fetch': ['api_request', 'file_read'],
        'code_run': ['code_debug', 'run_command'],
        'code_debug': ['code_run', 'run_command'],
        'database_query': ['api_request', 'file_read'],
        'api_request': ['web_fetch', 'database_query'],
        'image_process': ['file_edit', 'run_command'],
    }

    candidates = confusable.get(tool, all_tools.copy())
    return [t for t in candidates if t != tool and t in all_tools]


def generate_hard_negatives(query: str, tool: str, all_tools: List[str], n: int = 5) -> List[Tuple[str, str]]:
    """
    Generate hard negative query-tool pairs.

    Hard negatives are queries that look similar to the original but
    should route to a different (confusable) tool.

    Args:
        query: Original query
        tool: The correct tool for the query
        all_tools: List of all available tool names
        n: Number of hard negatives to generate

    Returns:
        List of (negative_query, wrong_tool) tuples
    """
    if not all_tools:
        from data.tools import get_tool_names
        all_tools = get_tool_names()

    confusable_tools = _get_confusable_tools(tool, all_tools)
    if not confusable_tools:
        confusable_tools = [t for t in all_tools if t != tool][:n]

    hard_negatives = []

    # Generate variations that would trigger wrong tools
    for wrong_tool in confusable_tools[:n]:
        # Create query variations that could be mistaken for wrong_tool
        if wrong_tool == 'safe_delete' and 'delete' not in query.lower():
            neg_query = query.replace('clear', 'delete').replace('remove', 'delete').replace('erase', 'delete')
            if neg_query == query:
                neg_query = f"delete {query}"
        elif wrong_tool == 'memory_write' and 'write' not in query.lower():
            neg_query = query.replace('save', 'write').replace('store', 'write')
            if neg_query == query:
                neg_query = f"save {query}"
        elif wrong_tool == 'memory_search' and 'search' not in query.lower():
            neg_query = query.replace('find', 'search').replace('look', 'search')
            if neg_query == query:
                neg_query = f"search for {query}"
        elif wrong_tool == 'file_read' and 'read' not in query.lower():
            neg_query = f"show me the contents of {query}"
        elif wrong_tool == 'git_commit' and 'commit' not in query.lower():
            neg_query = f"save my changes: {query}"
        elif wrong_tool == 'git_push' and 'push' not in query.lower():
            neg_query = f"upload my code: {query}"
        else:
            # Generic transformation
            neg_query = f"{query} (but different intent)"

        hard_negatives.append((neg_query, wrong_tool))

    return hard_negatives[:n]


def augment_dataset(dataset) -> List[Dict]:
    """
    Augment a dataset with paraphrases and hard negatives.

    Creates 15x expansion: 1 original → 10 paraphrases + 5 hard negatives

    Args:
        dataset: RosEnnaDataset or list of {query, tool, text} dicts

    Returns:
        List of augmented examples
    """
    from data.tools import get_tool_names
    all_tools = get_tool_names()

    augmented = []

    # Handle both dataset objects and lists
    if hasattr(dataset, 'examples'):
        examples = dataset.examples
    elif isinstance(dataset, list):
        examples = dataset
    else:
        return []

    for example in examples:
        query = example['query']
        tool = example['tool']
        text = example['text']

        # Add original
        augmented.append({'query': query, 'tool': tool, 'text': text})

        # Generate paraphrases (positives)
        paraphrases = generate_paraphrases(query, n=10)
        for para in paraphrases:
            augmented.append({'query': para, 'tool': tool, 'text': text})

        # Generate hard negatives
        hard_negs = generate_hard_negatives(query, tool, all_tools, n=5)
        for neg_query, neg_tool in hard_negs:
            # Get text for negative tool
            from data.tools import get_tool_text
            neg_text = get_tool_text(neg_tool)
            augmented.append({'query': neg_query, 'tool': neg_tool, 'text': neg_text})

    return augmented


class AugmentedDataset(Dataset):
    """
    Augmented dataset wrapper that generates on-the-fly augmentation.
    """

    def __init__(self, base_dataset, augmentation_factor: int = 15):
        """
        Args:
            base_dataset: Base RosEnnaDataset
            augmentation_factor: How many times to expand (15x default)
        """
        self.base = base_dataset
        self.augmentation_factor = augmentation_factor
        from data.tools import get_tool_names
        self.all_tools = get_tool_names()

    def __len__(self) -> int:
        return len(self.base) * self.augmentation_factor

    def __getitem__(self, idx: int) -> Dict:
        base_idx = idx % len(self.base)
        example = self.base[base_idx]
        position = idx // len(self.base)

        query = example['query']
        tool = example['tool']
        text = example['text']

        if position == 0:
            # Original
            return {'query': query, 'tool': tool, 'text': text, 'is_positive': True}
        elif position <= 10:
            # Paraphrase (positive)
            para_idx = position - 1
            paraphrases = generate_paraphrases(query, n=10)
            if para_idx < len(paraphrases):
                return {'query': paraphrases[para_idx], 'tool': tool, 'text': text, 'is_positive': True}
        else:
            # Hard negative
            neg_idx = position - 11
            hard_negs = generate_hard_negatives(query, tool, self.all_tools, n=5)
            if neg_idx < len(hard_negs):
                neg_query, neg_tool = hard_negs[neg_idx]
                from data.tools import get_tool_text
                neg_text = get_tool_text(neg_tool)
                return {'query': neg_query, 'tool': neg_tool, 'text': neg_text, 'is_positive': False}

        return {'query': query, 'tool': tool, 'text': text, 'is_positive': True}