CREATE TABLE "user" (
    user_id SERIAL PRIMARY KEY,
    user_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    user_role TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create a function to update the 'updated_at' column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger on the 'user' table
CREATE TRIGGER set_updated_at
BEFORE UPDATE ON "user"
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();

-- CLASS TABLE
CREATE TABLE class (
    class_id SERIAL PRIMARY KEY,
    class_name TEXT NOT NULL UNIQUE
);

-- PAST_PREDICTION TABLE
CREATE TABLE past_prediction (
    prediction_id SERIAL PRIMARY KEY,
    
    user_id INTEGER NOT NULL,
    image_uri TEXT NOT NULL,
    
    prediction INTEGER NOT NULL,  -- FK to class.class_id
    class_name TEXT,              -- Redundant display (optional)
    
    insertion_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

    modified_class INTEGER,       -- FK to class.class_id (corrected class)
    modified_class_name TEXT,     -- Redundant display (optional)
    modified_at TIMESTAMP,

    -- Foreign Keys
    CONSTRAINT fk_user
        FOREIGN KEY (user_id) REFERENCES "user"(user_id) ON DELETE CASCADE,

    CONSTRAINT fk_prediction_class
        FOREIGN KEY (prediction) REFERENCES class(class_id) ON DELETE SET NULL,

    CONSTRAINT fk_modified_class
        FOREIGN KEY (modified_class) REFERENCES class(class_id) ON DELETE SET NULL
);
