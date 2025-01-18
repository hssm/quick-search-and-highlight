def parse_search(search):
    terms = parse_nodes(search)
    return extract_searchable_terms(terms)


# Split search string by search terms
def parse_nodes(search):
    terms = []

    start = 0
    close = None
    level = 1
    backtrack = 0
    idx = -1
    for c in search:
        idx += 1
        # We're looking for a terminator
        if close:
            s_from = None
            s_to = None

            if close == ')' and c == '(':
                level += 1
                continue
            if close == ')' and c == ')':
                level -= 1
                if level > 0:
                    continue

            if ((c == '"' and close == '"')
                    or (c == "'" and close == "'")
                    or (c == ')' and close == ')')):
                close = None
                s_from = start
                s_to = idx+1
            if c == '"' and close == '\\s':
                close = '"'
                continue
            if c == '(' and close == '\\s':
                close = ')'
                continue
            elif c.isspace() and close == '\\s':
                close = None
                s_from = start
                s_to = idx
            # End of string. Force capture
            if idx == len(search)-1:
                close = None
                s_from = start
                s_to = idx+1

            # We captured a term
            if not close:
                terms.append(search[s_from-backtrack:s_to])
                start = idx+1
                backtrack = 0
                level = 1
        else:
            # We're looking for the beginning of a term
            if c == '"':
                close = '"'
            elif c == "'":
                close = "'"
            elif c == '(':
                close = ')'
            elif c == '-':
                backtrack += 1
                continue
            elif not c.isspace():
                close = '\\s'

            # We've started a capture
            if close:
                start = idx
                if idx == len(search) - 1:
                    # Capture started at end of string (single char term). Force capture.
                    terms.append(search[start:idx+1])
    return terms


# Pick out only the terms that result in a search of field string content.
# If the term is a (grouping) term, recursively extract terms from that too
def extract_searchable_terms(terms):
    extracted = []
    for term in terms:
        if not term:
            continue
        term = term.lower()
        if term[0] == '-':
            continue
        elif term.lower() == 'or' or term.lower() == 'and':
            continue
        elif term[0] == '(' and term[-1] == ')':
            inner_terms = parse_nodes(term[1:-1])
            extracted.extend(extract_searchable_terms(inner_terms))
            continue
        elif term[0] in ["'", '"']:
            if len(term) > 1:
                if ':' in term and term[term.index(':') - 1] != '\\':
                    pass
                else:
                    if term[1:-1].lower() in ['and', 'or']:
                        extracted.append({'tag': 'normal', 'term': term[1:-1]})
                    elif term[1] == '(' and term[-2] == ')':
                        extracted.append({'tag': 'quoted', 'term': term[1:-1]})
                    else:
                        if len(term) > 1 and term[0] == '"' and term[-1] == '"':
                            term = term[1:-1]
                        extracted.append({'tag': 'quoted', 'term': term})
                    continue
        if ':' in term and term[term.index(':') - 1] != '\\':
            if len(term) > 1 and term[0] == '"' and term[-1] == '"':
                term = term[1:-1]
            prefix, main = term.split(':', 1)

            if prefix in ignore:
                continue
            elif prefix == 'nc' or prefix == 'w': # Treat nc as a boundary. Should be enough for our case
                if len(main) > 1 and main[0] == '"' and main[-1] == '"':
                    main = main[1:-1]
                extracted.append({'tag': 'boundary', 'term': main})
            else:
                extracted.append({'tag': 'field', 'field_name': prefix, 'term': extract_searchable_terms([main])})

        else:
            # Replace wildcards before adding
            if '_' in term:
                index = term.index('_')
                if index == 0 or term[index - 1] != '\\':
                    term = term.replace('_', '.')
            if '*' in term:
                index = term.index('*')
                if index == 0 or term[index - 1] != '\\':
                    term = term.replace('*', '.*')
            if '\\:' in term:
                term = term.replace('\\:', ':')

            extracted.append({'tag': 'normal', 'term': term})
    return extracted

ignore = ['tag', 'deck', 'preset', 'card', 'is', 'flag', 'prop', 'added', 'edited', 'rated', 'introduced', 'nid', 'cid']

if __name__ == "__main__":
    for search in [
        "dog", "dog cat", "dog or cat", "dog (cat or mouse)", "-cat", "-cat -mouse", 'cat "and" mouse',
        "-(cat or mouse)", "d_g", "d*g", "w:dog", "w:dog*", "w:d_g", "w:*dog", 'w:"and also"', 'nc:"and also"',
        "front:dog", "front:*dog*", "front:",
        "front:_*", "front:*", "fr*:text", "back:(cat or mouse -dog)", '"animal front:a dog"', '"a dog"', '-"a dog"',

        # My tests
        "d\\g", "_og", "*og", "do_", "do*", "_do\\", '\\"dog\\"', "\\dog\\", '"(text)"', '\\(text\\)', '"\\(text\\)"',
        "w:3:30", "3\\:30",
    ]:
        # search = '"(text)"'
        nodes = parse_nodes(search)
        terms = extract_searchable_terms(nodes)
        print(nodes, "\t | \t", terms)