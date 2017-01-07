CREATE OR REPLACE FUNCTION devilry_dbcache_find_last_published_feedbackset_id_in_group(param_group_id integer)
RETURNS integer AS $$
DECLARE
    var_last_published_feedbackset_id integer;
BEGIN
    SELECT
        id INTO var_last_published_feedbackset_id
    FROM devilry_group_feedbackset
    WHERE group_id = param_group_id AND grading_published_datetime IS NOT NULL
    ORDER BY created_datetime DESC
    LIMIT 1;

    RETURN var_last_published_feedbackset_id;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION devilry_dbcache_on_feedbackset_insert_or_update(
    NEW_id INTEGER,
    NEW_group_id INTEGER,
    NEW_created_datetime TIMESTAMPTZ,
    NEW_grading_published_datetime TIMESTAMPTZ,
    param_operation text)
RETURNS VOID AS $$
DECLARE
    var_first_feedbackset_id integer;
    var_last_feedbackset_id integer;
    var_last_published_feedbackset_id integer;
    var_cached_data_exists boolean;
    var_cached_data record;
    var_feedbackset_count integer;
BEGIN
    SELECT
       EXISTS (SELECT 1 FROM devilry_dbcache_assignmentgroupcacheddata WHERE group_id = NEW_group_id)
       INTO var_cached_data_exists;


    RAISE NOTICE 'FEEDBACKSET - ID: %, group ID: %, CACHE-exists: %', NEW_id, NEW_group_id, var_cached_data_exists;

    IF NOT var_cached_data_exists THEN
        -- If the AssignmentGroupCachedData for feedbackset.group does NOT exist, create it
        -- We assume that if this is the first time we create an AssignmentGroupCachedData
        -- for the group, this is the first FeedbackSet in the group!
        IF NEW_grading_published_datetime IS NOT NULL THEN
            var_last_published_feedbackset_id := NEW_id;
        END IF;
        INSERT INTO devilry_dbcache_assignmentgroupcacheddata (
            group_id,
            first_feedbackset_id,
            last_feedbackset_id,
            last_published_feedbackset_id,
            feedbackset_count,
            public_total_comment_count,
            public_student_comment_count,
            public_examiner_comment_count,
            public_admin_comment_count,
            public_total_imageannotationcomment_count,
            public_student_imageannotationcomment_count,
            public_examiner_imageannotationcomment_count,
            public_admin_imageannotationcomment_count,
            file_upload_count_total,
            file_upload_count_student,
            file_upload_count_examiner)
        VALUES (
            NEW_group_id,
            NEW_id,
            NEW_id,
            var_last_published_feedbackset_id,
            1, -- feedbackset_count start on 1
            0,0,0,0,0,0,0,0,0,0,0);
    ELSE
        SELECT
            cached_data.group_id AS group_id,
            cached_data.first_feedbackset_id AS first_feedbackset_id,
            cached_data.last_feedbackset_id AS last_feedbackset_id,
            cached_data.last_published_feedbackset_id AS last_published_feedbackset_id,
            cached_data.feedbackset_count AS feedbackset_count,
            first_feedbackset.created_datetime AS first_feedbackset_created_datetime,
            last_feedbackset.created_datetime AS last_feedbackset_created_datetime,
            last_published_feedbackset.created_datetime AS last_published_feedbackset_created_datetime
        FROM devilry_dbcache_assignmentgroupcacheddata AS cached_data
        LEFT JOIN devilry_group_feedbackset first_feedbackset
            ON cached_data.first_feedbackset_id = first_feedbackset.id
        LEFT JOIN devilry_group_feedbackset last_feedbackset
            ON cached_data.last_feedbackset_id = last_feedbackset.id
        LEFT JOIN devilry_group_feedbackset last_published_feedbackset
            ON cached_data.last_published_feedbackset_id = last_published_feedbackset.id
        WHERE cached_data.group_id = NEW_group_id
        INTO var_cached_data;

        -- We only update the cache if any fields affecting the cache is changed
        IF NEW_created_datetime < var_cached_data.first_feedbackset_created_datetime THEN
            var_first_feedbackset_id := NEW_id;
        ELSE
            var_first_feedbackset_id := var_cached_data.first_feedbackset_id;
        END IF;

        IF NEW_created_datetime > var_cached_data.last_feedbackset_created_datetime THEN
            var_last_feedbackset_id := NEW_id;
        ELSE
            var_last_feedbackset_id := var_cached_data.last_feedbackset_id;
        END IF;

        var_feedbackset_count = var_cached_data.feedbackset_count;
        IF param_operation = 'INSERT' THEN
            var_feedbackset_count = var_feedbackset_count + 1;
        ELSE
            IF param_operation = 'DELETE' THEN
                var_feedbackset_count = var_feedbackset_count - 1;
            END IF;
        END IF;

        IF (var_cached_data.last_published_feedbackset_id IS NULL
            OR var_cached_data.last_published_feedbackset_id != NEW_id
            ) AND NEW_grading_published_datetime IS NOT NULL
            AND (
                var_cached_data.last_published_feedbackset_created_datetime IS NULL
                OR NEW_created_datetime > var_cached_data.last_published_feedbackset_created_datetime)
        THEN
            var_last_published_feedbackset_id := NEW_id;
        ELSE
            IF var_cached_data.last_published_feedbackset_id = NEW_id THEN
                -- This happens if we unpublish the currently last published feedbackset.
                -- We have to perform at SELECT query to find the correct value. This is a
                -- bit expensive, but it is not a problem since this rarely happens, and
                -- it will very rarely be done in bulk.
                var_last_published_feedbackset_id := devilry_dbcache_find_last_published_feedbackset_id_in_group(NEW_group_id);
            ELSE
                var_last_published_feedbackset_id := var_cached_data.last_published_feedbackset_id;
            END IF;
        END IF;

        UPDATE devilry_dbcache_assignmentgroupcacheddata
        SET
            first_feedbackset_id = var_first_feedbackset_id,
            last_feedbackset_id = var_last_feedbackset_id,
            last_published_feedbackset_id = var_last_published_feedbackset_id,
            feedbackset_count = var_feedbackset_count
        WHERE group_id = NEW_group_id;
    END IF;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION devilry_dbcache_on_feedbackset_insert_or_update_func_wrapper() RETURNS TRIGGER AS $$
BEGIN
    PERFORM devilry_dbcache_on_feedbackset_insert_or_update(NEW.id, NEW.group_id,
                                                            NEW.created_datetime,
                                                            NEW.grading_published_datetime,
                                                            TG_OP);
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS devilry_dbcache_on_feedbackset_insert_or_update_trigger
    ON devilry_group_feedbackset;
CREATE TRIGGER devilry_dbcache_on_feedbackset_insert_or_update_trigger
    AFTER INSERT OR UPDATE ON devilry_group_feedbackset
    FOR EACH ROW
        EXECUTE PROCEDURE devilry_dbcache_on_feedbackset_insert_or_update_func_wrapper();

/*
  Autocreate first FeedbackSet when creating an AssignmentGroup.
*/
CREATE OR REPLACE FUNCTION devilry_dbcache_on_assignmentgroup_insert() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO devilry_group_feedbackset (
        group_id,
        created_datetime,
        feedbackset_type,
        gradeform_data_json,
        ignored,
        ignored_reason)
    VALUES (
        NEW.id,
        now(),
        'first_attempt',
        '',
        FALSE,
        '');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS devilry_dbcache_on_assignmentgroup_insert_trigger
    ON core_assignmentgroup;
CREATE TRIGGER devilry_dbcache_on_assignmentgroup_insert_trigger
    AFTER INSERT ON core_assignmentgroup
    FOR EACH ROW
        EXECUTE PROCEDURE devilry_dbcache_on_assignmentgroup_insert();

/*
  Function to increment or decrement a value.
*/
CREATE OR REPLACE FUNCTION devilry_increment_or_decrement_value(value INTEGER, increment BOOLEAN) RETURNS INTEGER AS $$
BEGIN
    IF increment = TRUE THEN
        RETURN value + 1;
    ELSE
        RETURN value - 1;
    END IF;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION devilry_dbcache_on_group_or_imageannotationcomment_change(TG_OP VARCHAR,
                                                                                     record_feedback_set_id INTEGER,
                                                                                     record_comment_ptr_id INTEGER,
                                                                                     record_visibility VARCHAR)
RETURNS VOID AS $$
DECLARE
    var_user_role varchar;
    var_comment_type varchar;
    var_assignment_group_id integer;
    var_feedbackset_id record;
    var_increment boolean;
BEGIN

    IF TG_OP = 'INSERT' THEN
        var_increment = TRUE;
    ELSEIF TG_OP = 'DELETE' THEN
        var_increment = FALSE;
    END IF;

    SELECT group_id INTO var_assignment_group_id
    FROM devilry_group_feedbackset
    WHERE id = record_feedback_set_id;

    SELECT INTO var_comment_type, var_user_role
                    comment_type,     user_role
    FROM devilry_comment_comment
    WHERE id = record_comment_ptr_id;

    IF record_visibility = 'visible-to-everyone' THEN
        IF var_comment_type = 'groupcomment' THEN
            -- groupcomment
            UPDATE devilry_dbcache_assignmentgroupcacheddata
            SET public_total_comment_count = devilry_increment_or_decrement_value(public_total_comment_count, var_increment)
            WHERE group_id = var_assignment_group_id;

            IF var_user_role = 'student' THEN
                UPDATE devilry_dbcache_assignmentgroupcacheddata
                SET public_student_comment_count = devilry_increment_or_decrement_value(public_student_comment_count, var_increment)
                WHERE group_id = var_assignment_group_id;
            ELSEIF var_user_role = 'admin' THEN
               UPDATE devilry_dbcache_assignmentgroupcacheddata
                SET public_admin_comment_count = devilry_increment_or_decrement_value(public_admin_comment_count, var_increment)
                WHERE group_id = var_assignment_group_id;
            ELSEIF var_user_role = 'examiner' THEN
                UPDATE devilry_dbcache_assignmentgroupcacheddata
                SET public_examiner_comment_count = devilry_increment_or_decrement_value(public_examiner_comment_count, var_increment)
                WHERE group_id = var_assignment_group_id;
            END IF;
        ELSE
            -- imageannotationcomment
            UPDATE devilry_dbcache_assignmentgroupcacheddata
            SET public_total_imageannotationcomment_count = devilry_increment_or_decrement_value(public_total_imageannotationcomment_count, var_increment)
            WHERE group_id = var_assignment_group_id;

            IF var_user_role = 'student' THEN
                UPDATE devilry_dbcache_assignmentgroupcacheddata
                SET public_student_imageannotationcomment_count = devilry_increment_or_decrement_value(public_student_imageannotationcomment_count, var_increment)
                WHERE group_id = var_assignment_group_id;
            ELSEIF var_user_role = 'admin' THEN
               UPDATE devilry_dbcache_assignmentgroupcacheddata
                SET public_admin_imageannotationcomment_count = devilry_increment_or_decrement_value(public_admin_imageannotationcomment_count, var_increment)
                WHERE group_id = var_assignment_group_id;
            ELSEIF var_user_role = 'examiner' THEN
                UPDATE devilry_dbcache_assignmentgroupcacheddata
                SET public_examiner_imageannotationcomment_count = devilry_increment_or_decrement_value(public_examiner_imageannotationcomment_count, var_increment)
                WHERE group_id = var_assignment_group_id;
            END IF;
      END IF;
    END IF;
END
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION devilry_dbcache_on_group_or_imageannotationcomment_change_func_wrapper() RETURNS TRIGGER AS $$
DECLARE
       var_record record;
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'DELETE' THEN
        IF TG_OP = 'INSERT' THEN
            var_record = NEW;
        ELSEIF TG_OP = 'DELETE' THEN
            var_record = OLD;
        END IF;
        PERFORM devilry_dbcache_on_group_or_imageannotationcomment_change(TG_OP, var_record.feedback_set_id,
                                                                          var_record.comment_ptr_id,
                                                                          var_record.visibility);
    END IF;
    RETURN var_record;
END
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS devilry_dbcache_on_group_change_trigger
    ON devilry_group_groupcomment;
CREATE TRIGGER devilry_dbcache_on_group_change_trigger
    AFTER INSERT OR DELETE ON devilry_group_groupcomment
    FOR EACH ROW
        EXECUTE PROCEDURE devilry_dbcache_on_group_or_imageannotationcomment_change_func_wrapper();

DROP TRIGGER IF EXISTS devilry_dbcache_on_group_imageannotationcomment_trigger
    ON devilry_group_imageannotationcomment;
CREATE TRIGGER devilry_dbcache_on_group_imageannotationcomment_trigger
    AFTER INSERT OR DELETE ON devilry_group_imageannotationcomment
    FOR EACH ROW
        EXECUTE PROCEDURE devilry_dbcache_on_group_or_imageannotationcomment_change_func_wrapper();


CREATE OR REPLACE FUNCTION devilry_dbcache_on_file_upload_change(TG_OP VARCHAR, record_comment_id INTEGER)
RETURNS VOID AS $$
DECLARE
    var_user_role varchar;
    var_feedback_set_id integer;
    var_assignment_group_id integer;
    var_comment_type varchar;
    var_increment boolean;
    var_visibility varchar;
BEGIN

    IF TG_OP = 'INSERT' THEN
        var_increment = TRUE;
    ELSEIF TG_OP = 'DELETE' THEN
        var_increment = FALSE;
    END IF;

    SELECT INTO var_comment_type, var_user_role
                    comment_type,     user_role
    FROM devilry_comment_comment
    WHERE id = record_comment_id;

    IF var_comment_type = 'groupcomment' THEN
        SELECT INTO var_feedback_set_id, var_visibility
                        feedback_set_id,     visibility
        FROM devilry_group_groupcomment
        WHERE comment_ptr_id = record_comment_id;
    ELSEIF var_comment_type = 'imageannotationcomment' THEN
        SELECT INTO var_feedback_set_id, var_visibility
                        feedback_set_id,     visibility
        FROM devilry_group_imageannotationcomment
        WHERE comment_ptr_id = record_comment_id;
    END IF;

    SELECT group_id INTO var_assignment_group_id
    FROM devilry_group_feedbackset
    WHERE id = var_feedback_set_id;

    IF var_visibility = 'visible-to-everyone' THEN
        UPDATE devilry_dbcache_assignmentgroupcacheddata
        SET file_upload_count_total = devilry_increment_or_decrement_value(file_upload_count_total, var_increment)
        WHERE group_id = var_assignment_group_id;

        IF var_user_role = 'student' THEN
            UPDATE devilry_dbcache_assignmentgroupcacheddata
            SET file_upload_count_student = devilry_increment_or_decrement_value(file_upload_count_student, var_increment)
            WHERE group_id = var_assignment_group_id;
        ELSEIF var_user_role = 'examiner' THEN
            UPDATE devilry_dbcache_assignmentgroupcacheddata
            SET file_upload_count_examiner = devilry_increment_or_decrement_value(file_upload_count_examiner, var_increment)
            WHERE group_id = var_assignment_group_id;
        END IF;
    END IF;
END
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION devilry_dbcache_on_file_upload_change_func_wrapper() RETURNS TRIGGER AS $$
DECLARE
    var_record record;
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'DELETE' THEN
        IF TG_OP = 'INSERT' THEN
            var_record = NEW;
        ELSEIF TG_OP = 'DELETE' THEN
            var_record = OLD;
        END IF;
        PERFORM devilry_dbcache_on_file_upload_change(TG_OP, var_record.comment_id);
    END IF;
    RETURN var_record;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS devilry_dbcache_on_file_upload_change_trigger
    ON devilry_comment_commentfile;
CREATE TRIGGER devilry_dbcache_on_file_upload_change_trigger
    AFTER INSERT OR UPDATE OR DELETE ON devilry_comment_commentfile
    FOR EACH ROW
        EXECUTE PROCEDURE devilry_dbcache_on_file_upload_change_func_wrapper();



-- Rebuild AssignmentGroupCachedData table data.
CREATE OR REPLACE FUNCTION devilry_dbcache_rebuild_assignmentgroupcacheddata()
RETURNS void AS $$
BEGIN
    RAISE NOTICE 'Rebuilding data cache for Assignment Groups into table AssignmentGroupCachedData.';

    RAISE NOTICE 'Rebuilding data cache for table FeedbackSets...';
    PERFORM devilry_dbcache_on_feedbackset_insert_or_update(
        id,
        group_id,
        created_datetime,
        grading_published_datetime,
        'INSERT')
    FROM devilry_group_feedbackset;

    RAISE NOTICE 'Rebuilding data cache for table GroupComment...';
    PERFORM devilry_dbcache_on_group_or_imageannotationcomment_change('INSERT',
                                                                     feedback_set_id,
                                                                     comment_ptr_id,
                                                                     visibility)
    FROM devilry_group_groupcomment;

    RAISE NOTICE 'Rebuilding data cache for table ImageAnnotationComment...';
    PERFORM devilry_dbcache_on_group_or_imageannotationcomment_change('INSERT',
                                                                     feedback_set_id,
                                                                     comment_ptr_id,
                                                                     visibility)
    FROM devilry_group_imageannotationcomment;

    RAISE NOTICE 'Rebuilding data cache for table CommentFile...';
    PERFORM devilry_dbcache_on_file_upload_change('INSERT', comment_id)
    FROM devilry_comment_commentfile;

    RAISE NOTICE 'Rebuilding data cache finished.';
END
$$ LANGUAGE plpgsql;
