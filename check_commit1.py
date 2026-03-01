from cbra.store import create_thread, get_thread, get_field

def main():
    t = create_thread("test-thread")
    thread = get_thread("test-thread")
    assert thread is not None, "Thread was not created"
    assert thread.current_field_id, "Thread has no current_field_id"

    field = get_field(thread.current_field_id)
    assert field is not None, "Field was not created"
    assert field.thread_id == thread.id, "Field.thread_id does not match Thread.id"
    assert field.diffractive_ground == "CBRA"
    print("✅ Commit 1 check passed")
    print("Thread:", thread.id)
    print("Field:", field.id, "ground:", field.diffractive_ground)

if __name__ == "__main__":
    main()
