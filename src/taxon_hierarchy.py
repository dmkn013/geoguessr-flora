"""画像で確定した分類を、分類階層に沿って重複なく集計する。"""
from collections import Counter


def ancestors(name, parents):
    result, seen = [], {name}
    while name in parents:
        name = parents[name]
        if name in seen:
            raise ValueError('分類の親子関係に循環があります')
        seen.add(name)
        result.append(name)
    return result


def parent_names(catalog, legacy=None):
    """辞書の学名で指定した親を正式和名に変換。旧タグの対応も保持する。"""
    names = [entry['name'] for entry in catalog.values()]
    if len(names) != len(set(names)):
        raise ValueError('分類辞書に重複した正式名があります')
    parents = dict(legacy or {})
    for entry in catalog.values():
        parent = entry.get('parent')
        if parent:
            if parent not in catalog:
                raise ValueError(f'分類辞書に親がありません: {parent}')
            parents[entry['name']] = catalog[parent]['name']
    for name in parents:
        ancestors(name, parents)
    return parents


def expand_tags(names, parents):
    """同じ写真の複数個体・兄弟分類・明示的な親タグを二重に数えない。"""
    result = dict.fromkeys(names)
    for name in names:
        result.update(dict.fromkeys(ancestors(name, parents)))
    return list(result)


def most_specific(names, parents):
    covered = {parent for name in names for parent in ancestors(name, parents)}
    return list(dict.fromkeys(name for name in names if name not in covered))


def summarize_tags(image_tags, parents):
    direct, inclusive = Counter(), Counter()
    for names in image_tags.values():
        direct.update(set(names))
        inclusive.update(expand_tags(names, parents))
    return {
        'schema_version': 1,
        'count_unit': 'images',
        'reviewed_images': len(image_tags),
        'tagged_images': sum(bool(names) for names in image_tags.values()),
        'direct_image_counts': dict(sorted(direct.items())),
        'inclusive_image_counts': dict(sorted(inclusive.items())),
        'parent_of': dict(sorted(parents.items())),
    }
