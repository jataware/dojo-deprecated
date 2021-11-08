from validation import ModelSchema

def try_parse_int(s: str, default: int = 0) -> int:
    try:
        return int(s)
    except ValueError:
        return default

def delete_matching_records_from_model(model_id, record_key, record_test):

    from src.models import get_model, modify_model  # import at runtime to avoid circular import error
    record_count = 0

    model = get_model(model_id)
    records = model.get(record_key, [])
    records_to_delete = []
    for record in records:
        if record_test(record):
            records_to_delete.append(record)

    for record in records_to_delete:
        record_count += 1
        records.remove(record)

    update = { record_key: records }
    modify_model(model_id, ModelSchema.ModelMetadataPatchSchema(**update))

    return record_count